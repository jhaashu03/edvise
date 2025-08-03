"""
LangGraph Workflow Nodes for PDF Evaluation
Each node is a standalone function that can be tested and modified independently
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import existing services (maintaining compatibility)
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.api.llm_endpoints import comprehensive_question_analysis_direct
from app.services.topper_analysis_service import TopperAnalysisService
from app.core.llm_service import get_llm_service
from app.crud.answer import create_answer_evaluation
from app.schemas.answer import AnswerEvaluationCreate

from .pdf_evaluation_state import (
    PDFEvaluationState, 
    ProcessingPhase, 
    QuestionData, 
    EvaluationResult,
    ProgressUpdate,
    NodeResult
)

logger = logging.getLogger(__name__)


def get_db_session(config):
    """Extract db_session from LangGraph config"""
    if not config or "configurable" not in config:
        raise ValueError("Database session not available in config")
    db_session = config["configurable"].get("db_session")
    if not db_session:
        raise ValueError("Database session not found in config")
    return db_session


def get_progress_callback(config):
    """Extract progress_callback from LangGraph config"""
    if not config or "configurable" not in config:
        return None
    return config["configurable"].get("progress_callback")

async def validate_pdf_node(state: PDFEvaluationState) -> PDFEvaluationState:
    """
    Node 1: Validate PDF file and initialize processing
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 LangGraph Node 1: PDF Validation - Answer ID {state['answer_id']}")
        
        # Update state
        state["phase"] = ProcessingPhase.PDF_VALIDATION
        state["progress"] = 5.0
        state["processing_start_time"] = start_time.isoformat()
        
        # Validate file existence
        if not state["file_path"] or not os.path.exists(state["file_path"]):
            error_msg = f"PDF file not found: {state['file_path']}"
            state["errors"].append(error_msg)
            state["phase"] = ProcessingPhase.ERROR
            logger.error(f"❌ {error_msg}")
            return state
        
        # Extract basic PDF info
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(state["file_path"])
            state["total_pages"] = len(doc)
            state["pdf_filename"] = os.path.basename(state["file_path"])
            doc.close()
            logger.info(f"✅ PDF validated: {state['total_pages']} pages")
        except Exception as pdf_error:
            state["warnings"].append(f"Could not read PDF metadata: {pdf_error}")
            state["total_pages"] = 1  # Default assumption
            state["pdf_filename"] = os.path.basename(state["file_path"])
        
        # Send progress update
        if state.get("progress_callback"):
            progress_update = ProgressUpdate(
                phase=ProcessingPhase.PDF_VALIDATION,
                progress_percentage=5.0,
                current_step="PDF Validation",
                details=f"Validated PDF with {state['total_pages']} pages",
                questions_processed=0,
                total_questions=0,
                estimated_time_remaining=None,
                timestamp=datetime.now().isoformat()
            )
            state["progress_updates"].append(progress_update)
            
            # Call progress callback (compatible with existing WebSocket system)
            try:
                callback_data = {
                    "phase": "pdf_validation",
                    "progress": 5.0,
                    "details": f"Validated PDF with {state['total_pages']} pages",
                    "questions_processed": 0,
                    "total_questions": 0
                }
                
                if asyncio.iscoroutinefunction(state["progress_callback"]):
                    await state["progress_callback"](callback_data)
                else:
                    state["progress_callback"](callback_data)
            except Exception as callback_error:
                logger.warning(f"Progress callback failed: {callback_error}")
        
        logger.info(f"✅ PDF validation completed in {(datetime.now() - start_time).total_seconds():.2f}s")
        return state
        
    except Exception as e:
        error_msg = f"PDF validation failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["phase"] = ProcessingPhase.ERROR
        return state

async def extract_vision_node(state: PDFEvaluationState) -> PDFEvaluationState:
    """
    Node 2: Extract questions and answers using vision processing
    Uses existing VisionPDFProcessor for compatibility
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 LangGraph Node 2: Vision Extraction - {state['pdf_filename']}")
        
        # Update state
        state["phase"] = ProcessingPhase.VISION_EXTRACTION
        state["progress"] = 25.0
        
        # Create progress callback wrapper for VisionPDFProcessor
        async def vision_progress_wrapper(callback_data):
            """Wrapper to maintain compatibility with existing progress system"""
            if state.get("progress_callback"):
                try:
                    if asyncio.iscoroutinefunction(state["progress_callback"]):
                        await state["progress_callback"](callback_data)
                    else:
                        state["progress_callback"](callback_data)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
        
        # FIXED: Use vision extraction without comprehensive analysis to prevent duplication
        # The comprehensive analysis will be done by the analyze_dimensions_node
        from app.utils.vision_pdf_processor import VisionPDFProcessor
        
        processor = VisionPDFProcessor(progress_callback=vision_progress_wrapper)
        
        # Call the vision-only extraction method (without comprehensive analysis)
        extraction_result = await processor.extract_questions_only(
            state["file_path"],
            progress_callback=vision_progress_wrapper
        )
        
        if extraction_result and extraction_result.get("questions"):
            # Convert to standard format
            questions = []
            for q_data in extraction_result["questions"]:
                question = QuestionData(
                    question_number=q_data.get("question_number", len(questions) + 1),
                    question_text=q_data.get("question_text", "Question text not available"),
                    student_answer=q_data.get("student_answer", ""),
                    marks=q_data.get("marks", 10) or 10,  # Fix: Ensure marks is never None
                    page_number=q_data.get("page_number", 1),
                    word_limit=q_data.get("word_limit"),
                    time_limit=q_data.get("time_limit")
                )
                questions.append(question)
            
            state["questions"] = questions
            state["total_questions"] = len(questions)
            # Fix: Handle None marks values by defaulting to 10
            state["total_marks"] = sum(q["marks"] if q["marks"] is not None else 10 for q in questions)
            state["extraction_successful"] = True
            
            logger.info(f"✅ Vision extraction completed: {len(questions)} questions found")
            
        else:
            # Fallback to simple content analysis
            logger.warning("Vision extraction failed, using fallback content analysis")
            fallback_question = QuestionData(
                question_number=1,
                question_text="General Answer Analysis",
                student_answer=state["content"],
                marks=15,
                page_number=1,
                word_limit=250,
                time_limit=20
            )
            
            state["questions"] = [fallback_question]
            state["total_questions"] = 1
            state["total_marks"] = 15
            state["extraction_successful"] = False
            state["warnings"].append("Used fallback content analysis due to vision extraction failure")
        
        # Update progress
        state["progress"] = 40.0
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Vision extraction completed in {processing_time:.2f}s")
        
        return state
        
    except Exception as e:
        error_msg = f"Vision extraction failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["phase"] = ProcessingPhase.ERROR
        return state

async def analyze_dimensions_node(state: PDFEvaluationState) -> PDFEvaluationState:
    """
    Node 3: Perform 13-dimensional analysis for each question
    Uses existing comprehensive_question_analysis_direct for compatibility
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 LangGraph Node 3: 13D Analysis - {state['total_questions']} questions")
        
        # Update state
        state["phase"] = ProcessingPhase.DIMENSIONAL_ANALYSIS
        state["progress"] = 50.0
        
        # Get LLM service
        llm_service = get_llm_service()
        
        # Process each question
        evaluations = []
        total_current_score = 0.0
        total_max_score = 0.0
        
        for idx, question_data in enumerate(state["questions"]):
            try:
                question_start = datetime.now()
                logger.info(f"Analyzing Q{question_data['question_number']}: {question_data['question_text'][:50]}...")
                
                # Use existing comprehensive analysis (maintains compatibility)
                analysis_result = await comprehensive_question_analysis_direct(
                    question=question_data["question_text"],
                    student_answer=question_data["student_answer"],
                    exam_context={
                        "marks": question_data["marks"],
                        "time_limit": question_data.get("time_limit", 20),
                        "word_limit": question_data.get("word_limit", 250),
                        "exam_type": "UPSC Mains"
                    },
                    llm_service=llm_service,
                    question_number=str(question_data["question_number"])
                )
                
                if analysis_result.get("success"):
                    # Fixed: Use 'analysis' key instead of 'comprehensive_analysis'
                    analysis = analysis_result.get("analysis", {})
                    
                    # Log the analysis structure for debugging
                    logger.info(f"📊 ANALYSIS STRUCTURE for Q{question_data['question_number']}: Keys = {list(analysis.keys()) if analysis else 'None'}")
                    if "dimensional_scores" in analysis:
                        logger.info(f"✅ DIMENSIONAL SCORES FOUND for Q{question_data['question_number']}: {list(analysis['dimensional_scores'].keys())}")
                    else:
                        logger.warning(f"❌ NO DIMENSIONAL SCORES for Q{question_data['question_number']} - analysis keys: {list(analysis.keys()) if analysis else 'empty'}")
                    
                    answer_eval = analysis.get("answer_evaluation", {})
                    
                    # Extract scores (compatible with existing format)
                    current_score_str = answer_eval.get("current_score", f"{question_data['marks'] * 0.6:.0f}/{question_data['marks']}")
                    try:
                        current_score = float(current_score_str.split('/')[0])
                    except:
                        current_score = question_data["marks"] * 0.6
                    
                    # Create evaluation result
                    evaluation = EvaluationResult(
                        question_number=question_data["question_number"],
                        question_text=question_data["question_text"],
                        current_score=current_score,
                        max_score=float(question_data["marks"]),
                        detailed_feedback=analysis,
                        strengths=analysis.get("detailed_feedback", {}).get("strengths", []),
                        improvements=analysis.get("detailed_feedback", {}).get("improvement_suggestions", []),
                        topper_comparison=analysis.get("topper_analysis"),
                        processing_time=(datetime.now() - question_start).total_seconds()
                    )
                    
                    evaluations.append(evaluation)
                    total_current_score += current_score
                    total_max_score += question_data["marks"]
                    
                    # Send progress update
                    progress_percent = 50.0 + (idx + 1) / state["total_questions"] * 30.0
                    state["progress"] = progress_percent
                    
                    if state.get("progress_callback"):
                        try:
                            callback_data = {
                                "phase": "question_analysis", 
                                "progress": progress_percent,
                                "details": f"Analyzed question {idx + 1}/{state['total_questions']}",
                                "questions_processed": idx + 1,
                                "total_questions": state["total_questions"]
                            }
                            
                            if asyncio.iscoroutinefunction(state["progress_callback"]):
                                await state["progress_callback"](callback_data)
                            else:
                                state["progress_callback"](callback_data)
                        except Exception as callback_error:
                            logger.warning(f"Progress callback failed: {callback_error}")
                    
                    logger.info(f"✅ Q{question_data['question_number']} analyzed: {current_score}/{question_data['marks']}")
                    
                else:
                    error_msg = f"Analysis failed for Q{question_data['question_number']}: {analysis_result.get('error', 'Unknown error')}"
                    state["warnings"].append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
                    
            except Exception as question_error:
                error_msg = f"Error analyzing Q{question_data['question_number']}: {str(question_error)}"
                state["warnings"].append(error_msg)
                logger.error(f"❌ {error_msg}")
                continue
        
        # Update state with results
        state["evaluations"] = evaluations
        state["total_score"] = total_current_score
        state["total_max_score"] = total_max_score
        state["progress"] = 80.0
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ 13D analysis completed in {processing_time:.2f}s: {len(evaluations)} evaluations")
        
        return state
        
    except Exception as e:
        error_msg = f"13D analysis failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["phase"] = ProcessingPhase.ERROR
        return state

async def save_results_node(state: PDFEvaluationState) -> PDFEvaluationState:
    """
    Node 4: Save results to database
    Uses existing database models and CRUD operations for compatibility
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 LangGraph Node 4: Database Storage - Answer ID {state['answer_id']}")
        
        # Update state
        state["phase"] = ProcessingPhase.DATABASE_STORAGE
        state["progress"] = 90.0
        
        # Prepare evaluation data (compatible with existing format)
        if state["evaluations"]:
            # Use first evaluation's detailed feedback as primary
            primary_eval = state["evaluations"][0]
            detailed_feedback = primary_eval["detailed_feedback"]
            
            # Aggregate all evaluations
            all_strengths = []
            all_improvements = []
            
            for eval_result in state["evaluations"]:
                all_strengths.extend(eval_result.get("strengths", []))
                all_improvements.extend(eval_result.get("improvements", []))
            
            # Remove duplicates while preserving order
            unique_strengths = list(dict.fromkeys(all_strengths))
            unique_improvements = list(dict.fromkeys(all_improvements))
            
        else:
            # Fallback data
            detailed_feedback = {"error": "No evaluations completed"}
            unique_strengths = []
            unique_improvements = []
        
        # Create evaluation record (using existing CRUD)
        evaluation_data = AnswerEvaluationCreate(
            answer_id=state["answer_id"],
            score=state["total_score"],
            maxScore=state["total_max_score"],
            feedback=str(detailed_feedback),
            strengths="\n".join(unique_strengths) if unique_strengths else "No specific strengths identified",
            improvements="\n".join(unique_improvements) if unique_improvements else "No specific improvements identified",
            detailed_feedback=detailed_feedback
        )
        
        # Database save is handled by API endpoint - just mark as completed
        state["evaluation_created"] = True
        logger.info(f"✅ LangGraph workflow node completed - database save handled by API endpoint")
        
        # Prepare final result (compatible with existing system)
        state["final_result"] = {
            "success": len(state["errors"]) == 0,
            "pdf_filename": state["pdf_filename"],
            "total_questions_evaluated": len(state["evaluations"]),
            "total_score": state["total_score"],
            "total_max_score": state["total_max_score"],
            "questions": [
                {
                    "question_number": eval_result["question_number"],
                    "question_text": eval_result["question_text"],
                    "current_score": eval_result["current_score"],
                    "max_score": eval_result["max_score"],
                    "detailed_feedback": eval_result["detailed_feedback"]
                }
                for eval_result in state["evaluations"]
            ],
            "processing_time": (datetime.now() - datetime.fromisoformat(state["processing_start_time"])).total_seconds(),
            "extraction_method": "vision" if state["extraction_successful"] else "fallback",
            "warnings": state["warnings"],
            "errors": state["errors"]
        }
        
        # Update final state
        state["phase"] = ProcessingPhase.COMPLETED
        state["progress"] = 100.0
        state["processing_end_time"] = datetime.now().isoformat()
        
        # Final progress update
        if state.get("progress_callback"):
            try:
                callback_data = {
                    "phase": "completed",
                    "progress": 100.0,
                    "details": f"Evaluation completed: {state['total_score']:.1f}/{state['total_max_score']:.1f}",
                    "questions_processed": len(state["evaluations"]),
                    "total_questions": state["total_questions"]
                }
                
                if asyncio.iscoroutinefunction(state["progress_callback"]):
                    await state["progress_callback"](callback_data)
                else:
                    state["progress_callback"](callback_data)
            except Exception as callback_error:
                logger.warning(f"Final progress callback failed: {callback_error}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Results saved in {processing_time:.2f}s")
        
        return state
        
    except Exception as e:
        error_msg = f"Results saving failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["phase"] = ProcessingPhase.ERROR
        return state

async def handle_error_node(state: PDFEvaluationState) -> PDFEvaluationState:
    """
    Error handling node - provides fallback analysis
    Ensures system never completely fails
    """
    try:
        logger.info(f"🔍 LangGraph Error Handler - Answer ID {state['answer_id']}")
        
        # Update state
        state["phase"] = ProcessingPhase.ERROR
        
        # Create minimal fallback evaluation
        fallback_evaluation = AnswerEvaluationCreate(
            answer_id=state["answer_id"],
            score=7.5,  # Default score
            maxScore=15.0,
            feedback="Automated evaluation temporarily unavailable. Manual review recommended.",
            strengths="Answer submitted for evaluation",
            improvements="Manual review recommended for detailed feedback",
            detailed_feedback={
                "error": "Evaluation system encountered technical difficulties",
                "errors": state["errors"],
                "warnings": state["warnings"],
                "fallback_applied": True
            }
        )
        
        # Attempt to save fallback evaluation
        try:
            evaluation_record = create_answer_evaluation(
                db=state["db_session"],
                evaluation=fallback_evaluation
            )
            state["evaluation_created"] = True
            logger.info(f"✅ Fallback evaluation saved: ID {evaluation_record.id}")
            
        except Exception as db_error:
            logger.error(f"❌ Even fallback save failed: {db_error}")
            state["evaluation_created"] = False
        
        # Prepare error result
        state["final_result"] = {
            "success": False,
            "error": "Evaluation system encountered technical difficulties",
            "errors": state["errors"],
            "warnings": state["warnings"],
            "fallback_applied": True,
            "pdf_filename": state.get("pdf_filename"),
            "total_questions_evaluated": 0,
            "total_score": 7.5,
            "total_max_score": 15.0
        }
        
        # Error progress update
        if state.get("progress_callback"):
            try:
                callback_data = {
                    "phase": "error",
                    "progress": 100.0,
                    "details": "Evaluation completed with errors - fallback applied",
                    "questions_processed": 0,
                    "total_questions": 1
                }
                
                if asyncio.iscoroutinefunction(state["progress_callback"]):
                    await state["progress_callback"](callback_data)
                else:
                    state["progress_callback"](callback_data)
            except Exception as callback_error:
                logger.warning(f"Error progress callback failed: {callback_error}")
        
        logger.warning(f"⚠️ Error handling completed with fallback evaluation")
        
        return state
        
    except Exception as e:
        logger.error(f"❌ Critical error in error handler: {str(e)}")
        # Ensure we always return a state even in worst case
        state["final_result"] = {
            "success": False,
            "error": "Critical system error",
            "errors": state.get("errors", []) + [str(e)]
        }
        return state
