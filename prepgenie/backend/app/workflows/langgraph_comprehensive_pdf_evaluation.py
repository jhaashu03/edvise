"""
LangGraph Comprehensive PDF Evaluation Entry Point

This module provides the main entry point for the LangGraph-based comprehensive
PDF evaluation workflow. It acts as a compatibility layer between the existing
API and the new LangGraph workflow system.
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session

from .pdf_evaluation_workflow import PDFEvaluationWorkflow
from .pdf_evaluation_state import PDFEvaluationState, ProcessingPhase

logger = logging.getLogger(__name__)

async def langgraph_comprehensive_pdf_evaluation(
    answer_id: int,
    file_path: str,
    content: str,
    db_session: Session,
    progress_callback: Optional[Callable[[str, float, Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Main entry point for LangGraph-based comprehensive PDF evaluation.
    
    This function provides a compatible interface with the existing evaluation
    system while utilizing the new LangGraph workflow architecture.
    
    Args:
        answer_id: The answer ID for evaluation
        file_path: Path to the PDF file to evaluate
        content: Text content of the PDF (optional fallback)
        db_session: Database session for operations
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dict containing evaluation results and metadata
        
    Raises:
        Exception: If workflow execution fails critically
    """
    logger.info(f"🚀 Starting LangGraph PDF evaluation for answer {answer_id}")
    
    try:
        # Initialize the LangGraph workflow
        workflow = PDFEvaluationWorkflow()
        
        # Create initial state (without non-serializable objects)
        initial_state: PDFEvaluationState = {
            "answer_id": answer_id,
            "file_path": file_path,
            "content": content,
            "phase": ProcessingPhase.INITIALIZING,
            
            # Initialize all required state fields
            "questions": [],
            "analysis_results": [],
            "total_score": 0.0,
            "total_questions": 0,
            "evaluation_metadata": {},
            "errors": [],
            "warnings": [],
            "processing_stats": {
                "start_time": None,
                "end_time": None,
                "total_duration_seconds": 0.0,
                "questions_processed": 0,
                "avg_processing_time_per_question": 0.0
            },
            "workflow_metadata": {
                "workflow_type": "langgraph",
                "version": "1.0",
                "node_execution_log": []
            }
        }
        
        # Send initial progress update
        if progress_callback:
            await progress_callback({
                "phase": "initializing", 
                "progress": 0.0,
                "message": "Initializing LangGraph PDF evaluation workflow...",
                "workflow": "langgraph"
            })
        
        # Execute the workflow (pass non-serializable objects via config)
        logger.info(f"🔄 Executing LangGraph workflow for answer {answer_id}")
        final_state = await workflow.run(initial_state, db_session=db_session, progress_callback=progress_callback)
        
        # Check if workflow completed successfully
        if final_state["phase"] == ProcessingPhase.ERROR:
            error_msg = f"LangGraph workflow failed: {final_state['errors']}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        # Send final progress update
        if progress_callback:
            await progress_callback({
                "phase": "completed", 
                "progress": 100.0,
                "message": "LangGraph PDF evaluation completed successfully!",
                "total_questions": final_state["total_questions"],
                "total_score": final_state["total_score"],
                "processing_time": final_state.get("processing_stats", {}).get("total_duration_seconds", 0.0)
            })
        
        # Prepare results in compatible format
        total_score = final_state.get("total_score", 0.0)
        total_max_score = final_state.get("total_max_score", 30.0)
        total_score_formatted = f"{total_score}/{total_max_score}"
        
        results = {
            "success": True,
            "workflow_type": "langgraph",
            "answer_id": answer_id,
            "total_questions": final_state["total_questions"],
            "total_score": total_score_formatted,  # Format as "current/max" string
            "total_questions_evaluated": final_state["total_questions"],  # Add field expected by API
            "questions_processed": len(final_state.get("analysis_results", [])),
            "question_evaluations": final_state.get("evaluations", []),  # Add the expected field
            "processing_stats": final_state.get("processing_stats", {
                "start_time": None,
                "end_time": None,
                "total_duration_seconds": 0.0,
                "questions_processed": 0,
                "avg_processing_time_per_question": 0.0
            }),
            "evaluation_metadata": final_state.get("evaluation_metadata", {}),
            "workflow_metadata": final_state.get("workflow_metadata", {
                "workflow_type": "langgraph",
                "version": "1.0",
                "node_execution_log": []
            }),
            "errors": final_state["errors"],
            "warnings": final_state["warnings"]
        }
        
        logger.info(f"✅ LangGraph evaluation completed successfully for answer {answer_id}")
        logger.info(f"📊 Results: {final_state['total_questions']} questions, score: {final_state['total_score']:.2f}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ LangGraph evaluation failed for answer {answer_id}: {str(e)}")
        
        # Send error progress update
        if progress_callback:
            await progress_callback({
                "phase": "error", 
                "progress": 0.0,
                "message": f"LangGraph evaluation failed: {str(e)}",
                "error": str(e)
            })
        
        # Return error results in compatible format
        return {
            "success": False,
            "workflow_type": "langgraph",
            "answer_id": answer_id,
            "error": str(e),
            "total_questions": 0,
            "total_score": 0.0,
            "questions_processed": 0,
            "processing_stats": {
                "start_time": None,
                "end_time": None,
                "total_duration_seconds": 0.0,
                "questions_processed": 0,
                "avg_processing_time_per_question": 0.0
            },
            "errors": [str(e)],
            "warnings": []
        }

# Export the main function
__all__ = ["langgraph_comprehensive_pdf_evaluation"]
