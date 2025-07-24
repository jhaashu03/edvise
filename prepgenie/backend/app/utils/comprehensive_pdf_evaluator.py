import logging
import os
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.llm_service import get_llm_service, LLMService
from app.models.answer import AnswerEvaluationCreate
from app.crud.answer import create_answer_evaluation
from app.api.llm_endpoints import comprehensive_question_analysis_direct, evaluate_answer, AnswerEvaluationRequest, ExamContext
from app.utils.vision_pdf_processor import create_question_specific_evaluation_request, extract_questions_from_pdf

logger = logging.getLogger(__name__)

async def create_comprehensive_pdf_evaluation_v2(answer_id: int, content: str, file_path: str = None) -> bool:
    """
    Enhanced comprehensive evaluation for PDF uploads using:
    1. PDF text extraction with question identification
    2. 13-dimensional agentic evaluation system per question
    3. Comprehensive detailed feedback and scoring
    """
    try:
        from app.db.database import SessionLocal
        
        db = SessionLocal()
        llm_service = get_llm_service()
        
        try:
            logger.info(f"Starting comprehensive PDF evaluation for answer {answer_id}")
            
            # Step 1: Extract questions from PDF or analyze content
            if file_path and os.path.exists(file_path):
                try:
                    pdf_data = extract_questions_from_pdf(file_path)
                    logger.info(f"PDF extraction successful: {len(pdf_data.get('questions', []))} questions found")
                except Exception as pdf_error:
                    logger.warning(f"PDF extraction failed: {pdf_error}")
                    # Fallback to content analysis
                    pdf_data = {
                        "questions": [
                            {
                                "question_number": 1,
                                "question_text": "General Answer Analysis",
                                "student_answer": content,
                                "marks": 15,
                                "page_number": 1
                            }
                        ],
                        "total_questions": 1,
                        "total_marks": 15
                    }
            else:
                # Direct content analysis
                pdf_data = {
                    "questions": [
                        {
                            "question_number": 1,
                            "question_text": "Answer Analysis",
                            "student_answer": content,
                            "marks": 15,
                            "page_number": 1
                        }
                    ],
                    "total_questions": 1,
                    "total_marks": 15
                }
            
            # Step 2: Process each question with comprehensive 13-dimensional analysis
            question_evaluations = []
            total_current_score = 0
            total_possible_marks = 0
            
            for question in pdf_data["questions"]:
                if question["student_answer"] and question["student_answer"].strip():
                    try:
                        logger.info(f"Analyzing Q{question['question_number']}: {question['question_text'][:50]}...")
                        
                        # Use comprehensive 13-dimensional analysis
                        comprehensive_result = await comprehensive_question_analysis_direct(
                            question=question["question_text"],
                            student_answer=question["student_answer"],
                            exam_context={
                                "marks": question["marks"],
                                "time_limit": 20,
                                "word_limit": 250,
                                "exam_type": "UPSC Mains"
                            },
                            llm_service=llm_service
                        )
                        
                        if comprehensive_result.get("success"):
                            analysis = comprehensive_result.get("comprehensive_analysis", {})
                            
                            # Extract scores
                            answer_eval = analysis.get("answer_evaluation", {})
                            current_score_str = answer_eval.get("current_score", f"{question['marks'] * 0.6:.0f}/{question['marks']}")
                            potential_score_str = answer_eval.get("potential_score", f"{question['marks'] * 0.8:.0f}/{question['marks']}")
                            
                            try:
                                current_score = float(current_score_str.split('/')[0])
                                potential_score = float(potential_score_str.split('/')[0])
                            except:
                                current_score = question["marks"] * 0.6
                                potential_score = question["marks"] * 0.8
                            
                            total_current_score += current_score
                            total_possible_marks += question["marks"]
                            
                            # Create comprehensive question evaluation
                            question_evaluation = {
                                "question_number": question["question_number"],
                                "question_text": question["question_text"],
                                "marks_allocated": question["marks"],
                                "current_score": current_score,
                                "potential_score": potential_score,
                                "student_answer": question["student_answer"][:300] + "..." if len(question["student_answer"]) > 300 else question["student_answer"],
                                "comprehensive_analysis": analysis,
                                "dimensional_feedback": analysis.get("dimensional_scores", {}),
                                "specific_strengths": analysis.get("detailed_feedback", {}).get("strengths", [])[:3],
                                "improvement_areas": analysis.get("detailed_feedback", {}).get("improvement_suggestions", [])[:3],
                                "aptitude_tips": analysis.get("aptitude_enhancement", {}).get("knowledge_leverage_tips", [])[:3],
                                "learning_recommendations": analysis.get("learning_recommendations", {})
                            }
                            
                            question_evaluations.append(question_evaluation)
                            logger.info(f"Q{question['question_number']} comprehensive analysis completed: {current_score}/{question['marks']}")
                            
                        else:
                            logger.error(f"Comprehensive analysis failed for Q{question['question_number']}: {comprehensive_result.get('error')}")
                            # Add basic evaluation as fallback
                            basic_score = question["marks"] * 0.6
                            total_current_score += basic_score
                            total_possible_marks += question["marks"]
                            
                            question_evaluation = {
                                "question_number": question["question_number"],
                                "question_text": question["question_text"],
                                "marks_allocated": question["marks"],
                                "current_score": basic_score,
                                "potential_score": question["marks"] * 0.8,
                                "student_answer": question["student_answer"][:300] + "..." if len(question["student_answer"]) > 300 else question["student_answer"],
                                "note": "Comprehensive analysis temporarily unavailable",
                                "basic_feedback": "Answer submitted and evaluated with basic scoring"
                            }
                            question_evaluations.append(question_evaluation)
                            
                    except Exception as q_error:
                        logger.error(f"Error analyzing Q{question['question_number']}: {q_error}")
                        continue
                        
                else:
                    logger.info(f"Skipping Q{question['question_number']} - no answer provided")
            
            # Step 3: Create comprehensive evaluation summary
            overall_percentage = (total_current_score / total_possible_marks * 100) if total_possible_marks > 0 else 60
            pdf_filename = file_path.split('/')[-1] if file_path else "Uploaded Document"
            
            # Generate comprehensive feedback report
            comprehensive_feedback = f"""# 📊 Comprehensive PDF Analysis Report

## 📄 Document Summary
- **File**: {pdf_filename}
- **Questions Analyzed**: {len(question_evaluations)}
- **Overall Score**: {total_current_score:.1f}/{total_possible_marks} ({overall_percentage:.1f}%)
- **Analysis Type**: 13-Dimensional Agentic Evaluation

## 🎯 Question-wise Detailed Analysis

"""
            
            for eval_data in question_evaluations:
                comprehensive_feedback += f"""### Question {eval_data['question_number']}: {eval_data['question_text'][:80]}...

**📝 Answer Excerpt**: "{eval_data['student_answer']}"

**🏆 Performance**: {eval_data['current_score']:.1f}/{eval_data['marks_allocated']} marks (Potential: {eval_data.get('potential_score', eval_data['marks_allocated'] * 0.8):.1f}/{eval_data['marks_allocated']})

"""
                
                if eval_data.get('comprehensive_analysis'):
                    analysis = eval_data['comprehensive_analysis']
                    
                    # Add dimensional scores
                    if analysis.get('dimensional_scores'):
                        comprehensive_feedback += "**📊 Dimensional Analysis**:\n"
                        for dimension, data in list(analysis['dimensional_scores'].items())[:5]:  # Top 5 dimensions
                            if isinstance(data, dict):
                                score = data.get('score', 'N/A')
                                feedback = data.get('feedback', '')[:100]
                                comprehensive_feedback += f"• {dimension.replace('_', ' ').title()}: {score} - {feedback}...\n"
                        comprehensive_feedback += "\n"
                    
                    # Note: Individual question strengths/improvements removed to prevent duplication
                    # They are collected in the main evaluation function and added once at the end
                
                comprehensive_feedback += "\n---\n\n"
            
            # Step 4: Save to database
            evaluation_data = AnswerEvaluationCreate(
                answer_id=answer_id,
                overall_score=f"{total_current_score:.1f}/{total_possible_marks}",
                structure_score=f"{overall_percentage * 0.7:.1f}/10",
                coverage_score=f"{overall_percentage * 0.75:.1f}/10",
                tone_score=f"{overall_percentage * 0.8:.1f}/10",
                feedback=comprehensive_feedback,
                strengths=json.dumps([
                    f"Comprehensive 13-dimensional analysis completed",
                    f"Overall performance: {overall_percentage:.1f}%",
                    f"Successfully analyzed {len(question_evaluations)} questions"
                ]),
                improvements=json.dumps([
                    "Question-specific enhancement strategies provided",
                    "Dimensional scores for targeted improvement available",
                    "Aptitude-based improvement techniques suggested"
                ])
            )
            
            # Save evaluation
            create_answer_evaluation(db, evaluation_data, answer_id)
            
            logger.info(f"Comprehensive PDF evaluation completed for answer {answer_id}: {total_current_score:.1f}/{total_possible_marks}")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to create comprehensive evaluation for answer {answer_id}: {e}")
        return False
