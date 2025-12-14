from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import uuid
import time
import traceback
import asyncio
from pathlib import Path
import json
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.answer import UploadedAnswer as Answer, AnswerEvaluation as Evaluation
from app.api.api_v1.endpoints.auth import get_current_user
from app.schemas.answer import (
    AnswerCreate, AnswerResponse, AnswerUploadResponse, 
    AnswerEvaluation, AnswerEvaluationSchema,
    AnswerEvaluationCreate, EvaluationOption, EvaluationRequest
)
from app.core.config import settings
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.core.llm_service import get_llm_service, LLMService
from app.utils.vision_pdf_processor import ProgressTracker
from app.services.topper_comparison_service import TopperComparisonService
from app.db.database import SessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)

# Force reload test v3

# Helper functions
async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return the file path"""
    upload_dir = Path(settings.UPLOAD_DIR) / "answers"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    filename = f"{file_id}{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    logger.info(f"File saved to {file_path}")
    return str(file_path)

# Background task functions for separate evaluation types
async def dimensional_pdf_evaluation(answer_id: int, file_path: str, task_id: str, paper_subject: str = None):
    """
    Background task for 13-dimensional AI evaluation only.
    
    Args:
        answer_id: ID of the answer to evaluate
        file_path: Path to the PDF file
        task_id: Unique task ID for progress tracking
        paper_subject: Optional paper-level subject (gs1, gs2, gs3, gs4, anthropology).
                      If provided, all questions use this subject's rubric.
    """
    local_db = SessionLocal()
    
    try:
        if paper_subject:
            logger.info(f"🔍 Starting 13-dimensional evaluation for answer {answer_id} with paper subject: {paper_subject.upper()}")
        else:
            logger.info(f"🔍 Starting 13-dimensional evaluation for answer {answer_id} (auto-detect subjects)")
        
        # Import the vision processor function
        from app.utils.vision_pdf_processor import process_vision_pdf_with_evaluation
        
        # Add progress callback for dimensional evaluation
        from app.api.websocket_progress import progress_manager
        from datetime import datetime
        
        def progress_callback(callback_data: dict):
            """Send progress updates via WebSocket"""
            try:
                # Use asyncio.create_task to schedule the coroutine
                import asyncio
                try:
                    # Try to get the current event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule the task
                        asyncio.create_task(progress_manager.send_progress_update(task_id, {
                            "progress": callback_data.get("progress", 0),
                            "message": callback_data.get("message", "Processing..."),
                            "timestamp": datetime.now().isoformat(),
                            "phase": callback_data.get("phase"),
                            "details": callback_data.get("details")
                        }))
                    else:
                        # If no loop is running, run until complete
                        loop.run_until_complete(progress_manager.send_progress_update(task_id, {
                            "progress": callback_data.get("progress", 0),
                            "message": callback_data.get("message", "Processing..."),
                            "timestamp": datetime.now().isoformat(),
                            "phase": callback_data.get("phase"),
                            "details": callback_data.get("details")
                        }))
                except RuntimeError:
                    # If there's an event loop issue, just log and continue
                    logger.debug(f"Progress update skipped due to event loop conflict: {callback_data.get('message', 'Processing...')}")
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")
        
        # Process PDF with dimensional evaluation
        evaluation_results = await process_vision_pdf_with_evaluation(
            file_path=file_path,
            answer_id=answer_id,
            db=local_db,
            progress_callback=progress_callback,
            paper_subject=paper_subject  # Pass paper-level subject for consistent evaluation
        )
        
        if evaluation_results and evaluation_results.get('question_evaluations'):
            question_evaluations = evaluation_results['question_evaluations']
            total_questions = len(question_evaluations)
            
            # Calculate scores from dimensional evaluation
            total_score = 0.0
            max_score = total_questions * 10.0
            
            # Extract dimensional scores
            total_structure_score = 0.0
            total_coverage_score = 0.0
            total_tone_score = 0.0
            valid_evaluations = 0
            
            logger.info(f"Processing {len(question_evaluations)} question evaluations")
            for i, q_eval in enumerate(question_evaluations):
                # Check for answer_evaluation field
                if isinstance(q_eval, dict) and q_eval.get('answer_evaluation'):
                    answer_evaluation = q_eval['answer_evaluation']
                    
                    if isinstance(answer_evaluation, dict):
                        # Look for dimensional_scores in answer_evaluation
                        dimensions = answer_evaluation.get('dimensional_scores', {})
                        
                        if dimensions:
                            # Parse scores helper function
                            def parse_score(score_str):
                                try:
                                    if isinstance(score_str, (int, float)):
                                        return float(score_str)
                                    elif isinstance(score_str, str) and '/' in score_str:
                                        return float(score_str.split('/')[0])
                                    return 0.0
                                except Exception:
                                    return 0.0
                            
                            # Extract all 13 dimensional scores
                            dimension_names = [
                                'Structure', 'Coverage', 'Tone_and_Language', 'Analytical_Thinking',
                                'Factual_Accuracy', 'Conceptual_Understanding', 'Examples_and_Illustrations',
                                'Balanced_Perspective', 'Conclusion', 'Relevance', 'Clarity', 'Depth', 'Presentation'
                            ]
                            
                            question_total = 0
                            valid_dimensions = 0
                            
                            for dim_name in dimension_names:
                                dim_data = dimensions.get(dim_name, {})
                                if isinstance(dim_data, dict):
                                    score = parse_score(dim_data.get('score', 0))
                                    question_total += score
                                    valid_dimensions += 1
                            
                            if valid_dimensions > 0:
                                question_avg = question_total / valid_dimensions
                                total_structure_score += question_avg
                                total_coverage_score += question_avg
                                total_tone_score += question_avg
                                valid_evaluations += 1
            
            # Calculate averages and collect detailed feedback
            detailed_feedback_sections = []
            all_strengths = []
            all_improvements = []
            
            if valid_evaluations > 0:
                avg_structure = total_structure_score / valid_evaluations
                avg_coverage = total_coverage_score / valid_evaluations
                avg_tone = total_tone_score / valid_evaluations
                total_score = (avg_structure + avg_coverage + avg_tone) * total_questions / 3
                
                # Collect detailed feedback from each question
                for i, q_eval in enumerate(question_evaluations):
                    if isinstance(q_eval, dict) and q_eval.get('answer_evaluation'):
                        answer_eval = q_eval['answer_evaluation']
                        if isinstance(answer_eval, dict):
                            # Add question-specific feedback
                            q_num = q_eval.get('question_number', f'Q{i+1}')
                            q_text = q_eval.get('question_text', 'Question text not available')[:100] + "..."
                            
                            detailed_feedback_sections.append(f"### 📝 {q_num}: {q_text}")
                            
                            # Add dimensional scores and feedback
                            dimensions = answer_eval.get('dimensional_scores', {})
                            if dimensions:
                                detailed_feedback_sections.append("**Dimensional Analysis:**")
                                for dim_name, dim_data in dimensions.items():
                                    if isinstance(dim_data, dict):
                                        score = dim_data.get('score', 0)
                                        feedback_text = dim_data.get('feedback', 'No feedback available')
                                        detailed_feedback_sections.append(f"- **{dim_name}** ({score}/10): {feedback_text}")
                            
                            # Collect strengths and improvements
                            if answer_eval.get('strengths'):
                                strengths = answer_eval.get('strengths', [])
                                if isinstance(strengths, list):
                                    all_strengths.extend(strengths)
                                elif isinstance(strengths, str):
                                    try:
                                        import ast
                                        all_strengths.extend(ast.literal_eval(strengths))
                                    except:
                                        all_strengths.append(strengths)
                            
                            if answer_eval.get('improvements'):
                                improvements = answer_eval.get('improvements', [])
                                if isinstance(improvements, list):
                                    all_improvements.extend(improvements)
                                elif isinstance(improvements, str):
                                    try:
                                        import ast
                                        all_improvements.extend(ast.literal_eval(improvements))
                                    except:
                                        all_improvements.append(improvements)
                            
                            detailed_feedback_sections.append("")  # Add spacing
                
            else:
                avg_structure = avg_coverage = avg_tone = 6.0
                total_score = total_questions * 6.0
            
            # Create comprehensive feedback with actual dimensional analysis
            feedback = f"""# 📊 13-Dimensional AI Analysis Results

**📈 Overall Performance**: {total_score:.1f}/{max_score:.0f} ({(total_score/max_score*100):.1f}%)
**📚 Questions Analyzed**: {total_questions}
**⚙️ Analysis Method**: 13-Dimensional AI Evaluation

## 🎯 Dimensional Scores:
- **Structure**: {avg_structure:.1f}/10
- **Coverage**: {avg_coverage:.1f}/10  
- **Tone & Language**: {avg_tone:.1f}/10

## 📋 Detailed Analysis:

{chr(10).join(detailed_feedback_sections) if detailed_feedback_sections else f'{len(question_evaluations)} questions were comprehensively analyzed across 13 key dimensions including structure, content coverage, tone, clarity, and more.'}

## 🚀 Key Strengths:
{chr(10).join([f'- {strength}' for strength in all_strengths[:5]]) if all_strengths else '''- Comprehensive AI-powered analysis completed
- All questions evaluated systematically
- Detailed dimensional scoring provided'''}

## 📈 Areas for Improvement:
{chr(10).join([f'- {improvement}' for improvement in all_improvements[:5]]) if all_improvements else '''- Review dimensional feedback for specific insights
- Focus on lower-scoring dimensions
- Practice structured answer writing'''}"""
            
            # Collect actionable data from all question evaluations
            all_actionable_data = {
                "questions": [],
                "total_questions": total_questions,
                "overall_score": total_score,
                "max_score": max_score,
                "avg_structure": avg_structure,
                "avg_coverage": avg_coverage,
                "avg_tone": avg_tone
            }
            
            for i, q_eval in enumerate(question_evaluations):
                if isinstance(q_eval, dict) and q_eval.get('answer_evaluation'):
                    answer_eval = q_eval['answer_evaluation']
                    if isinstance(answer_eval, dict):
                        # Extract actionable fields for frontend display
                        question_actionable = {
                            "question_number": q_eval.get('question_number', i + 1),
                            "question_text": q_eval.get('question_text', ''),
                            "marks": q_eval.get('marks', 10),
                            "detected_subject": answer_eval.get('detected_subject'),
                            "demand_analysis": answer_eval.get('demand_analysis'),
                            "structure": answer_eval.get('structure'),
                            "content_quality": answer_eval.get('content_quality'),
                            "examples": answer_eval.get('examples'),
                            "diagram_suggestion": answer_eval.get('diagram_suggestion'),
                            "value_additions": answer_eval.get('value_additions'),
                            "presentation": answer_eval.get('presentation'),
                            "overall_score": answer_eval.get('overall_score'),
                            "quick_verdict": answer_eval.get('quick_verdict'),
                            "top_3_improvements": answer_eval.get('top_3_improvements'),
                            "dimensional_scores": answer_eval.get('dimensional_scores'),
                            "strengths": answer_eval.get('strengths', []),
                            "improvements": answer_eval.get('improvements', [])
                        }
                        all_actionable_data["questions"].append(question_actionable)
            
            # Create evaluation record
            from app.crud.answer import create_answer_evaluation
            evaluation_data = AnswerEvaluationCreate(
                score=total_score,
                max_score=max_score,
                feedback=feedback,
                strengths=str([
                    "13-dimensional analysis completed",
                    f"All {total_questions} questions evaluated",
                    "AI-powered comprehensive feedback",
                    "Structured dimensional scoring"
                ]),
                improvements=str([
                    "Review dimensional scores for insights",
                    "Focus on improving lower-scoring areas",
                    "Practice structured answer techniques",
                    "Enhance content depth and clarity"
                ]),
                structure=avg_structure,
                coverage=avg_coverage,
                tone=avg_tone,
                actionable_data=json.dumps(all_actionable_data)  # Store full actionable data
            )
            
            create_answer_evaluation(local_db, evaluation_data, answer_id)
            logger.info(f"✅ 13-dimensional evaluation completed for answer {answer_id}")
            
            # Send final completion signal to frontend
            try:
                import asyncio
                async def send_completion():
                    await progress_manager.send_progress_update(task_id, {
                        "progress": 100,
                        "message": "✅ Evaluation Complete - Results Ready!",
                        "timestamp": datetime.now().isoformat(),
                        "phase": "completed",
                        "details": "Evaluation finished successfully",
                        "status": "completed",
                        "answer_id": answer_id
                    })
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(send_completion())
                    else:
                        loop.run_until_complete(send_completion())
                except RuntimeError:
                    logger.debug("Completion signal skipped due to event loop conflict")
            except Exception as e:
                logger.warning(f"Failed to send completion signal: {e}")
            
        else:
            logger.error(f"❌ Failed to process PDF for dimensional evaluation: {answer_id}")
            
            # Send error completion signal
            try:
                import asyncio
                async def send_error():
                    await progress_manager.send_progress_update(task_id, {
                        "progress": 100,
                        "message": "❌ Evaluation Failed",
                        "timestamp": datetime.now().isoformat(),
                        "phase": "error",
                        "details": "PDF processing failed",
                        "status": "error",
                        "answer_id": answer_id
                    })
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(send_error())
                    else:
                        loop.run_until_complete(send_error())
                except RuntimeError:
                    logger.debug("Error signal skipped due to event loop conflict")
            except Exception as e:
                logger.warning(f"Failed to send error signal: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error in dimensional evaluation: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Send error completion signal
        try:
            import asyncio
            error_message = str(e)
            async def send_error():
                await progress_manager.send_progress_update(task_id, {
                    "progress": 100,
                    "message": "❌ Evaluation Error",
                    "timestamp": datetime.now().isoformat(),
                    "phase": "error",
                    "details": f"Error: {error_message[:100]}",
                    "status": "error",
                    "answer_id": answer_id
                })
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(send_error())
                else:
                    loop.run_until_complete(send_error())
            except RuntimeError:
                logger.debug("Error signal skipped due to event loop conflict")
        except Exception as signal_error:
            logger.warning(f"Failed to send error signal: {signal_error}")
    finally:
        local_db.close()

async def topper_comparison_evaluation(answer_id: int, file_path: str, task_id: str):
    """Background task for topper comparison evaluation only"""
    local_db = SessionLocal()
    
    try:
        logger.info(f" Starting topper comparison evaluation for answer {answer_id}")
        
        # Extract content from PDF using vision processor (questions only, no 13D evaluation)
        from app.utils.vision_pdf_processor import VisionPDFProcessor
        from app.api.websocket_progress import progress_manager
        from datetime import datetime
        
        def progress_callback(callback_data: dict):
            """Send progress updates via WebSocket"""
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(progress_manager.send_progress_update(task_id, {
                            "progress": callback_data.get("progress", 0),
                            "message": callback_data.get("message", "Processing..."),
                            "timestamp": datetime.now().isoformat(),
                            "phase": callback_data.get("phase"),
                            "details": callback_data.get("details")
                        }))
                    else:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(progress_manager.send_progress_update(task_id, {
                            "progress": callback_data.get("progress", 0),
                            "message": callback_data.get("message", "Processing..."),
                            "timestamp": datetime.now().isoformat(),
                            "phase": callback_data.get("phase"),
                            "details": callback_data.get("details")
                        }))
                except RuntimeError:
                    logger.debug("Progress update skipped due to event loop conflict")
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")
        
        # Extract questions and answers only (no 13D evaluation)
        processor = VisionPDFProcessor(progress_callback=progress_callback)
        pdf_results = await processor.extract_questions_only(file_path, progress_callback)
        
        if pdf_results and pdf_results.get('questions'):
            # Process ALL questions for topper comparison
            questions = pdf_results['questions']
            logger.info(f"📋 Questions data type: {type(questions)}, length: {len(questions) if questions else 0}")
            
            if questions:
                # Handle both dict and list formats
                if isinstance(questions, dict):
                    questions_list = list(questions.values())
                    logger.info(f"📋 Converted dict to list: {len(questions_list)} questions")
                elif isinstance(questions, list):
                    questions_list = questions
                    logger.info(f"📋 Using list directly: {len(questions_list)} questions")
                else:
                    logger.error(f"Unexpected questions format: {type(questions)}")
                    return
                
                # Debug first question structure
                if questions_list:
                    first_q = questions_list[0]
                    logger.info(f"📋 First question keys: {list(first_q.keys()) if isinstance(first_q, dict) else 'Not a dict'}")
                    logger.info(f"📋 First question sample: {str(first_q)[:200]}...")
                
                # Initialize topper comparison service
                topper_service = TopperComparisonService()
                
                # Process each question individually
                all_topper_evaluations = []
                for i, question in enumerate(questions_list):
                    question_text = question.get('question_text', '')
                    student_answer = question.get('student_answer', '')  # Changed from 'complete_answer' to 'student_answer'
                    marks_data = question.get('marks', '10')  # Changed from nested metadata to direct 'marks' field
                    
                    # Parse marks from string like "10 marks" or "15"
                    import re
                    marks_match = re.search(r'\d+', str(marks_data))
                    marks = int(marks_match.group()) if marks_match else 10
                    
                    # Skip if no question or answer
                    if not question_text.strip() or not student_answer.strip():
                        logger.warning(f"Skipping Q{i+1}: question_text='{question_text[:50]}...', student_answer='{student_answer[:50]}...'")
                        continue
                    
                    logger.info(f"Processing Q{i+1}: '{question_text[:100]}...' with {len(student_answer)} chars")
                    
                    # Perform topper comparison for this specific question
                    topper_evaluation = await topper_service.generate_topper_based_evaluation(
                        question_text=question_text,
                        student_answer=student_answer,
                        marks=marks
                    )
                    
                    # Add question number and details
                    topper_evaluation['question_number'] = i + 1
                    topper_evaluation['question_text'] = question_text[:100] + "..." if len(question_text) > 100 else question_text
                    
                    all_topper_evaluations.append(topper_evaluation)
                    
                    # Send progress update for each question
                    progress_percentage = 50 + (30 * (i + 1) / len(questions_list))  # 50-80% range
                    await progress_manager.send_progress_update(task_id, {
                        "progress": int(progress_percentage),
                        "message": f"📊 Analyzing Question {i+1} with Toppers",
                        "timestamp": datetime.now().isoformat(),
                        "phase": "topper_comparison",
                        "details": f"Comparing Q{i+1} with topper answers",
                        "answer_id": answer_id
                    })
                
                # Combine all evaluations into comprehensive feedback
                if all_topper_evaluations:
                    combined_feedback = []
                    total_score = 0
                    total_max_score = 0
                    
                    for eval_result in all_topper_evaluations:
                        q_num = eval_result.get('question_number', 1)
                        q_text = eval_result.get('question_text', 'Question')
                        
                        combined_feedback.append(f"\n🔍 **QUESTION {q_num} ANALYSIS**")
                        combined_feedback.append(f"**Question**: {q_text}")
                        combined_feedback.append(f"**Score**: {eval_result.get('score', 0)}/{eval_result.get('max_score', 10)}")
                        combined_feedback.append("---")
                        combined_feedback.append(eval_result.get('feedback', 'No feedback available'))
                        combined_feedback.append("\n" + "="*50 + "\n")
                        
                        total_score += eval_result.get('score', 0)
                        total_max_score += eval_result.get('max_score', 10)
                    
                    # Create final combined evaluation
                    topper_evaluation = {
                        'evaluation_type': 'topper_comparison_multi_question',
                        'comparison_available': True,
                        'total_score': round(total_score, 1),
                        'total_max_score': total_max_score,
                        'questions_analyzed': len(all_topper_evaluations),
                        'feedback': '\n'.join(combined_feedback),
                        'individual_evaluations': all_topper_evaluations
                    }
                else:
                    topper_evaluation = {
                        'evaluation_type': 'topper_comparison',
                        'comparison_available': False,
                        'score': 0.0,
                        'max_score': 0.0,
                        'feedback': 'No valid questions found for topper comparison'
                    }
            
            # Create evaluation record in database
            if topper_evaluation:
                # Calculate proper dimensional scores from individual evaluations
                total_structure = sum(eval_result.get('structure', 0) for eval_result in all_topper_evaluations)
                total_coverage = sum(eval_result.get('coverage', 0) for eval_result in all_topper_evaluations)
                total_tone = sum(eval_result.get('tone', 0) for eval_result in all_topper_evaluations)
                
                evaluation_record = Evaluation(
                    answer_id=answer_id,
                    score=topper_evaluation.get('total_score', 0.0),
                    max_score=topper_evaluation.get('total_max_score', 10.0),
                    feedback=topper_evaluation.get('feedback', 'Topper comparison completed'),
                    structure=round(total_structure, 1),
                    coverage=round(total_coverage, 1),
                    tone=round(total_tone, 1),
                    strengths=json.dumps(topper_evaluation.get('topper_insights', {}).get('student_strengths', [])),
                    improvements=json.dumps(topper_evaluation.get('topper_insights', {}).get('specific_improvements', []))
                )
                
                local_db.add(evaluation_record)
                local_db.commit()
                local_db.refresh(evaluation_record)
                
                logger.info(f"✅ Topper comparison evaluation saved for answer {answer_id}")
                
                # Send final completion signal to frontend
                try:
                    import asyncio
                    async def send_completion():
                        await progress_manager.send_progress_update(task_id, {
                            "progress": 100,
                            "message": "✅ Topper Comparison Complete - Results Ready!",
                            "timestamp": datetime.now().isoformat(),
                            "phase": "completed",
                            "details": "Topper comparison finished successfully",
                            "status": "completed",
                            "answer_id": answer_id
                        })
                    
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(send_completion())
                        else:
                            loop.run_until_complete(send_completion())
                    except RuntimeError:
                        logger.debug("Completion signal skipped due to event loop conflict")
                except Exception as e:
                    logger.warning(f"Failed to send completion signal: {e}")
        else:
            logger.error(f"❌ Failed to extract content from PDF for answer {answer_id}")
            evaluation = None
        
        if topper_evaluation:
            logger.info(f"✅ Topper comparison evaluation completed for answer {answer_id}")
        else:
            logger.error(f"❌ Failed to generate topper comparison evaluation for answer {answer_id}")
            
            # Send error completion signal
            try:
                import asyncio
                async def send_error():
                    await progress_manager.send_progress_update(task_id, {
                        "progress": 100,
                        "message": "❌ Topper Comparison Failed",
                        "timestamp": datetime.now().isoformat(),
                        "phase": "error",
                        "details": "Topper comparison processing failed",
                        "status": "error",
                        "answer_id": answer_id
                    })
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(send_error())
                    else:
                        loop.run_until_complete(send_error())
                except RuntimeError:
                    logger.debug("Error signal skipped due to event loop conflict")
            except Exception as e:
                logger.warning(f"Failed to send error signal: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error in topper comparison evaluation: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Send error completion signal
        try:
            import asyncio
            async def send_error():
                await progress_manager.send_progress_update(task_id, {
                    "progress": 100,
                    "message": "❌ Topper Comparison Error",
                    "timestamp": datetime.now().isoformat(),
                    "phase": "error",
                    "details": "Topper comparison processing failed",
                    "status": "error",
                    "answer_id": answer_id
                })
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(send_error())
                else:
                    loop.run_until_complete(send_error())
            except RuntimeError:
                logger.debug("Error signal skipped due to event loop conflict")
        except Exception as signal_error:
            logger.warning(f"Failed to send error signal: {signal_error}")
    finally:
        local_db.close()

# Legacy function - kept for backward compatibility but deprecated
def comprehensive_pdf_evaluation(answer_id: int, file_path: str, evaluation_type: str = "dimensional"):
    """
    DEPRECATED: Use dimensional_pdf_evaluation() or topper_comparison_evaluation() instead.
    This function is kept for backward compatibility only.
    """
    logger.warning(f"Using deprecated comprehensive_pdf_evaluation for answer {answer_id}. Use separate evaluation functions instead.")
    
    # Route to appropriate evaluation function based on type
    if evaluation_type == "topper_comparison":
        import asyncio
        asyncio.create_task(topper_comparison_evaluation(answer_id, file_path))
    else:
        import asyncio
        asyncio.create_task(dimensional_pdf_evaluation(answer_id, file_path))


def _create_topper_comparison_evaluation(answer_id: int, evaluation_results: dict, local_db):
    """Create topper comparison based evaluation"""
    try:
        from app.services.topper_comparison_service import TopperComparisonService
        
        logger.info(f"Creating topper comparison evaluation for answer {answer_id}")
        
        # Extract question and answer from evaluation results
        if "question_evaluations" in evaluation_results and len(evaluation_results["question_evaluations"]) > 0:
            first_question = evaluation_results["question_evaluations"][0]
            question_text = first_question.get("question_text", "")
            student_answer = first_question.get("student_answer", "")
            marks = first_question.get("marks", 10)
            
            # Initialize topper comparison service
            topper_service = TopperComparisonService()
            
            # Generate topper-based evaluation (this is async but we'll handle it)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                topper_evaluation = loop.run_until_complete(
                    topper_service.generate_topper_based_evaluation(question_text, student_answer, marks)
                )
                
                # Create evaluation record
                new_evaluation = Evaluation(
                    answer_id=answer_id,
                    score=topper_evaluation.get('score', 0.0),
                    max_score=topper_evaluation.get('max_score', 10.0),
                    feedback=topper_evaluation.get('feedback', 'Topper comparison evaluation completed'),
                    structure=topper_evaluation.get('structure', 7.0),
                    coverage=topper_evaluation.get('coverage', 6.0),
                    tone=topper_evaluation.get('tone', 7.0),
                    strengths=json.dumps(topper_evaluation.get('topper_insights', {}).get('student_strengths', [])),
                    improvements=json.dumps(topper_evaluation.get('topper_insights', {}).get('specific_improvements', []))
                )
                
                local_db.add(new_evaluation)
                local_db.commit()
                local_db.refresh(new_evaluation)
                
                logger.info(f"✅ SUCCESS: Topper comparison evaluation created with ID: {new_evaluation.id}")
                
            finally:
                loop.close()
        else:
            # Fallback evaluation
            fallback_evaluation = Evaluation(
                answer_id=answer_id,
                score=0.0,
                max_score=10.0,
                feedback="No questions found for topper comparison",
                structure=0.0,
                coverage=0.0,
                tone=0.0,
                strengths="[]",
                improvements="[]"
            )
            local_db.add(fallback_evaluation)
            local_db.commit()
            logger.info(f"Created fallback topper evaluation with ID: {fallback_evaluation.id}")
            
    except Exception as e:
        logger.error(f"Error creating topper comparison evaluation: {e}")
        # Create emergency fallback
        emergency_evaluation = Evaluation(
            answer_id=answer_id,
            score=0.0,
            max_score=10.0,
            feedback=f"Topper comparison failed: {str(e)}",
            structure=0.0,
            coverage=0.0,
            tone=0.0,
            strengths="[]",
            improvements="[]"
        )
        local_db.add(emergency_evaluation)
        local_db.commit()


# Add new endpoint for evaluation options
@router.get("/evaluation-options")
def get_evaluation_options(
    current_user: User = Depends(get_current_user)
):
    """Get available evaluation options"""
    return [
        EvaluationOption(
            type="dimensional",
            name="13-Dimensional Analysis",
            description="Comprehensive evaluation across 13 dimensions including content knowledge, structure, analytical thinking, and presentation quality"
        ),
        EvaluationOption(
            type="topper_comparison", 
            name="Topper Comparison Analysis",
            description="Compare your answer with high-scoring topper answers to identify gaps, learn best practices, and get targeted improvement suggestions"
        )
    ]


# Modified upload endpoint to support evaluation type selection
@router.post("/upload", response_model=AnswerUploadResponse)
async def upload_answer_with_evaluation_option(
    file: UploadFile = File(...),
    question_id: str = Form(...),
    evaluation_request: str = Form(default='{"evaluation_type": "dimensional"}'),  # JSON string
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload answer with evaluation type selection"""
    try:
        # Parse evaluation request
        try:
            eval_req = json.loads(evaluation_request)
            evaluation_type = eval_req.get("evaluation_type", "dimensional")
        except json.JSONDecodeError:
            evaluation_type = "dimensional"  # Default fallback
        
        logger.info(f"Upload request with evaluation_type: {evaluation_type}")
        
        # Save uploaded file
        file_path = await save_uploaded_file(file)
        
        # Generate task ID for progress tracking
        task_id = f"pdf_eval_{int(time.time() * 1000)}_{current_user.id}"
        
        # Create answer record
        answer = Answer(
            user_id=current_user.id,
            question_id=question_id,
            content="PDF file uploaded for evaluation",
            file_path=file_path,
            task_id=task_id,
            processing_progress=0.0
        )
        
        db.add(answer)
        db.commit()
        db.refresh(answer)
        
        logger.info(f"✅ Answer saved successfully: ID={answer.id}, file_path={answer.file_path}")
        
        # Don't auto-start evaluation - let users choose evaluation type after upload
        # The evaluation will be started when user selects an evaluation type via separate endpoints
        
        # Create response
        answer_response = AnswerResponse(
            id=answer.id,
            question_id=answer.question_id,
            content=answer.content,
            file_path=answer.file_path,
            file_name=file.filename,
            uploaded_at=answer.uploaded_at.isoformat()
        )
        
        return AnswerUploadResponse(
            id=answer.id,
            message="Answer uploaded successfully. Choose your evaluation type to begin analysis.",
            answer=answer_response,
            task_id=None,  # No task_id since evaluation hasn't started yet
            processing_started=True
        )
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Keep existing upload endpoint for backward compatibility  
@router.post("/upload-legacy", response_model=AnswerUploadResponse)
async def upload_answer_legacy(
    file: UploadFile = File(...),
    question_id: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy upload endpoint - uses dimensional evaluation by default"""
    return await upload_answer_with_evaluation_option(
        file=file,
        question_id=question_id,
        evaluation_request='{"evaluation_type": "dimensional"}',
        background_tasks=background_tasks,
        current_user=current_user,
        db=db
    )


# Helper function to create topper comparison evaluation
async def create_topper_comparison_evaluation(answer_id: int, file_path: str, db: Session):
    """Create evaluation using topper comparison approach"""
    try:
        from app.services.topper_comparison_service import TopperComparisonService
        
        # Initialize topper comparison service
        topper_service = TopperComparisonService()
        
        # Generate topper-based evaluation
        evaluation_result = await topper_service.generate_topper_based_evaluation(
            answer_id=answer_id,
            file_path=file_path,
            db=db
        )
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Error in topper comparison evaluation: {e}")
        raise


# Background task for comprehensive PDF evaluation with dual evaluation support
def comprehensive_pdf_evaluation(answer_id: int, file_path: str, evaluation_type: str = "dimensional"):
    """
    Comprehensive PDF evaluation background task with dual evaluation support
    
    Args:
        answer_id: ID of the uploaded answer
        file_path: Path to the PDF file
        evaluation_type: Type of evaluation ("dimensional" or "topper_comparison")
    """
    logger.info(f"Starting {evaluation_type} evaluation for answer_id={answer_id}")
    
    # Create a new database session for the background task
    from app.db.database import SessionLocal
    local_db = SessionLocal()
    
    try:
        if evaluation_type == "topper_comparison":
            # Use topper comparison evaluation
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    create_topper_comparison_evaluation(answer_id, file_path, local_db)
                )
                logger.info(f"✅ Topper comparison evaluation completed for answer_id={answer_id}")
            finally:
                loop.close()
        else:
            # Use traditional dimensional evaluation
            from app.utils.vision_pdf_processor import process_vision_pdf_with_evaluation
            
            result = process_vision_pdf_with_evaluation(
                file_path=file_path,
                answer_id=answer_id,
                db=local_db
            )
            logger.info(f"✅ Dimensional evaluation completed for answer_id={answer_id}")
            
    except Exception as e:
        logger.error(f"Error in {evaluation_type} evaluation: {e}")
        # Create fallback evaluation
        try:
            from app.models.answer import AnswerEvaluation
            fallback_evaluation = AnswerEvaluation(
                answer_id=answer_id,
                score=0.0,
                max_score=30.0,
                feedback=f"Evaluation failed: {str(e)}",
                structure=0.0,
                coverage=0.0,
                tone=0.0,
                strengths="[]",
                improvements="[]"
            )
            local_db.add(fallback_evaluation)
            local_db.commit()
            logger.info(f"Created fallback evaluation for answer_id={answer_id}")
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback evaluation: {fallback_error}")
    
    finally:
        local_db.close()
        logger.info(f"Background task completed for answer_id={answer_id}")


# Get available evaluation options
@router.get("/evaluation-options", response_model=List[EvaluationOption])
async def get_evaluation_options():
    """Get available evaluation options for answer evaluation"""
    return [
        EvaluationOption(
            type="dimensional",
            name="13-Dimensional Analysis",
            description="Comprehensive evaluation across 13 dimensions including content knowledge, structure, analytical thinking, and presentation quality"
        ),
        EvaluationOption(
            type="topper_comparison", 
            name="Topper Comparison Analysis",
            description="Compare your answer against high-scoring topper answers to identify gaps, improvements, and learn from best practices"
        )
    ]


# Existing endpoints continue below...


@router.get("/{answer_id}/evaluation")
async def get_answer_evaluation(
    answer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation for a specific answer"""
    # Check if answer belongs to current user
    answer = db.query(Answer).filter(
        Answer.id == answer_id,
        Answer.user_id == current_user.id
    ).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # Get evaluation
    evaluation = db.query(Evaluation).filter(Evaluation.answer_id == answer_id).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return evaluation


@router.get("/me")
async def get_my_answers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all answers for the current user with their evaluations"""
    answers = db.query(Answer).filter(Answer.user_id == current_user.id).order_by(Answer.uploaded_at.desc()).all()
    logger.info(f"📋 Found {len(answers)} answers for user {current_user.id}")
    
    result = []
    for answer in answers:
        evaluation = db.query(Evaluation).filter(Evaluation.answer_id == answer.id).first()
        
        # Convert evaluation to proper format or None
        evaluation_data = None
        if evaluation:
            evaluation_data = {
                "id": evaluation.id,
                "answer_id": evaluation.answer_id,
                "score": evaluation.score,
                "max_score": evaluation.max_score,
                "feedback": evaluation.feedback,
                "strengths": evaluation.strengths,
                "improvements": evaluation.improvements,
                "structure": evaluation.structure,
                "coverage": evaluation.coverage,
                "tone": evaluation.tone,
                "evaluated_at": evaluation.evaluated_at.isoformat() if evaluation.evaluated_at else None
            }
            
            # Parse and include actionable data if available
            if hasattr(evaluation, 'actionable_data') and evaluation.actionable_data:
                try:
                    actionable = json.loads(evaluation.actionable_data)
                    # Merge actionable fields into evaluation_data for frontend
                    if actionable.get('questions') and len(actionable['questions']) > 0:
                        # Get first question's actionable data for summary display
                        first_q = actionable['questions'][0]
                        evaluation_data.update({
                            "detected_subject": first_q.get('detected_subject'),
                            "demand_analysis": first_q.get('demand_analysis'),
                            "structure_analysis": first_q.get('structure'),
                            "content_quality": first_q.get('content_quality'),
                            "examples": first_q.get('examples'),
                            "diagram_suggestion": first_q.get('diagram_suggestion'),
                            "value_additions": first_q.get('value_additions'),
                            "presentation": first_q.get('presentation'),
                            "overall_score": first_q.get('overall_score') or evaluation.score,
                            "quick_verdict": first_q.get('quick_verdict'),
                            "top_3_improvements": first_q.get('top_3_improvements'),
                            "dimensional_scores": first_q.get('dimensional_scores'),
                            # Include all questions for multi-question PDFs
                            "all_questions": actionable.get('questions', [])
                        })
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse actionable_data: {e}")
        
        answer_data = {
            "id": answer.id,
            "question_id": answer.question_id,
            "content": answer.content,
            "filePath": answer.file_path,  # Frontend expects filePath, not file_path
            "fileName": answer.file_path.split('/')[-1] if answer.file_path else None,
            "uploadedAt": answer.uploaded_at.isoformat() if answer.uploaded_at else None,
            "evaluation": evaluation_data
        }
        result.append(answer_data)
    
    return result


@router.get("/{answer_id}/evaluation", response_model=AnswerEvaluationSchema)
def get_answer_evaluation(
    answer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation for a specific answer"""
    # Get the answer first to check ownership
    answer = db.query(Answer).filter(
        Answer.id == answer_id,
        Answer.user_id == current_user.id
    ).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    if not answer.evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return AnswerEvaluationSchema(
        id=answer.evaluation.id,
        answer_id=answer.evaluation.answer_id,
        score=answer.evaluation.score,
        max_score=answer.evaluation.max_score,
        feedback=answer.evaluation.feedback,
        strengths=answer.evaluation.strengths,
        improvements=answer.evaluation.improvements,
        structure=answer.evaluation.structure,
        coverage=answer.evaluation.coverage,
        tone=answer.evaluation.tone,
        evaluated_at=answer.evaluation.evaluated_at.isoformat()
    )

@router.post("/{answer_id}/evaluate/dimensional")
async def evaluate_dimensional(
    answer_id: int,
    background_tasks: BackgroundTasks,
    paper_subject: Optional[str] = None,  # Paper-level subject: gs1, gs2, gs3, gs4, anthropology
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start 13-dimensional AI evaluation for an answer.
    
    Args:
        answer_id: ID of the answer to evaluate
        paper_subject: Optional paper-level subject override (gs1, gs2, gs3, gs4, anthropology).
                      If provided, ALL questions in the PDF will use this subject's evaluation rubric.
                      If not provided, subject will be auto-detected per-question.
    """
    # Verify answer ownership
    answer = db.query(Answer).filter(
        Answer.id == answer_id,
        Answer.user_id == current_user.id
    ).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    if not answer.file_path or not answer.file_path.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files can be evaluated")
    
    # Check if evaluation already exists
    existing_evaluation = db.query(Evaluation).filter(
        Evaluation.answer_id == answer_id
    ).first()
    
    if existing_evaluation:
        raise HTTPException(status_code=400, detail="Answer already has an evaluation")
    
    # Validate paper_subject if provided
    valid_subjects = ["gs1", "gs2", "gs3", "gs4", "anthropology", None]
    if paper_subject and paper_subject.lower() not in valid_subjects:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid paper_subject. Must be one of: gs1, gs2, gs3, gs4, anthropology"
        )
    
    # Generate task ID for tracking
    task_id = f"dimensional_eval_{answer_id}_{uuid.uuid4().hex[:8]}"
    
    # Log paper subject setting
    if paper_subject:
        logger.info(f"📋 Using paper-level subject override: {paper_subject.upper()}")
    else:
        logger.info(f"📋 No paper subject specified - will auto-detect per question")
    
    # Start background evaluation with task_id and paper_subject
    background_tasks.add_task(
        dimensional_pdf_evaluation,
        answer_id,
        answer.file_path,
        task_id,
        paper_subject.lower() if paper_subject else None
    )
    
    logger.info(f"Started 13-dimensional evaluation for answer {answer_id}")
    
    return {
        "message": "13-dimensional AI evaluation started",
        "task_id": task_id,
        "evaluation_type": "dimensional",
        "answer_id": answer_id,
        "paper_subject": paper_subject
    }

@router.post("/{answer_id}/evaluate/topper-comparison")
async def evaluate_topper_comparison(
    answer_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start topper comparison evaluation for an answer"""
    # Verify answer ownership
    answer = db.query(Answer).filter(
        Answer.id == answer_id,
        Answer.user_id == current_user.id
    ).first()
    
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    if not answer.file_path or not answer.file_path.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files can be evaluated")
    
    # Check if evaluation already exists
    existing_evaluation = db.query(Evaluation).filter(
        Evaluation.answer_id == answer_id
    ).first()
    
    if existing_evaluation:
        raise HTTPException(status_code=400, detail="Answer already has an evaluation")
    
    # Generate task ID for tracking
    task_id = f"topper_eval_{answer_id}_{uuid.uuid4().hex[:8]}"
    
    # Start background evaluation with task_id
    background_tasks.add_task(
        topper_comparison_evaluation,
        answer_id,
        answer.file_path,
        task_id
    )
    
    logger.info(f"Started topper comparison evaluation for answer {answer_id}")
    
    return {
        "message": "Topper comparison evaluation started",
        "task_id": task_id,
        "evaluation_type": "topper_comparison",
        "answer_id": answer_id
    }

@router.get("/evaluation-options")
def get_evaluation_options():
    """Get available evaluation options for students"""
    return {
        "options": [
            {
                "id": "dimensional",
                "name": "13-Dimensional AI Analysis",
                "description": "Comprehensive AI evaluation across 13 key dimensions including structure, coverage, tone, and more",
                "features": [
                    "Detailed dimensional scoring",
                    "AI-powered feedback",
                    "Comprehensive analysis",
                    "Improvement suggestions"
                ],
                "estimated_time": "2-3 minutes"
            },
            {
                "id": "topper_comparison",
                "name": "Compare with Toppers",
                "description": "Compare your answer with high-scoring topper answers using semantic similarity",
                "features": [
                    "Topper answer comparison",
                    "Semantic similarity analysis",
                    "Best practices identification",
                    "Gap analysis"
                ],
                "estimated_time": "1-2 minutes"
            }
        ]
    }

@router.get("/processing-progress/{task_id}")
async def get_processing_progress(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get processing progress for a specific task"""
    progress_tracker = ProgressTracker()
    return progress_tracker.get_progress(task_id)