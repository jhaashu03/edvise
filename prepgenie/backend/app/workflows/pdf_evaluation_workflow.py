"""
LangGraph PDF Evaluation Workflow
Advanced orchestration for comprehensive PDF evaluation with full backward compatibility
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session

# LangGraph imports
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver  # Disabled to prevent serialization issues

# Our imports
from .pdf_evaluation_state import PDFEvaluationState, ProcessingPhase, WorkflowConfig
from .pdf_evaluation_nodes import (
    validate_pdf_node,
    extract_vision_node,
    analyze_dimensions_node,
    save_results_node,
    handle_error_node
)

logger = logging.getLogger(__name__)

class PDFEvaluationWorkflow:
    """
    LangGraph-powered PDF evaluation workflow
    Provides advanced orchestration while maintaining full backward compatibility
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        self.config = config or self._default_config()
        self.graph = self._build_graph()
        self.workflow = self.graph  # Alias for compatibility
        logger.info("🚀 LangGraph PDF Evaluation Workflow initialized")
    
    def _default_config(self) -> WorkflowConfig:
        """Default workflow configuration"""
        return WorkflowConfig(
            max_retries=3,
            timeout_seconds=900,  # 15 minutes
            enable_topper_comparison=True,
            enable_progress_streaming=True,
            fallback_on_error=True,
            detailed_logging=True
        )
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create graph
        graph = StateGraph(PDFEvaluationState)
        
        # Add nodes
        graph.add_node("validate_pdf", validate_pdf_node)
        graph.add_node("extract_vision", extract_vision_node)  
        graph.add_node("analyze_dimensions", analyze_dimensions_node)
        graph.add_node("save_results", save_results_node)
        graph.add_node("handle_error", handle_error_node)
        
        # Set entry point
        graph.set_entry_point("validate_pdf")
        
        # Add conditional edges for workflow control
        graph.add_conditional_edges(
            "validate_pdf",
            self._should_continue_after_validation,
            {
                "continue": "extract_vision",
                "error": "handle_error"
            }
        )
        
        graph.add_conditional_edges(
            "extract_vision", 
            self._should_continue_after_extraction,
            {
                "continue": "analyze_dimensions",
                "error": "handle_error"
            }
        )
        
        graph.add_conditional_edges(
            "analyze_dimensions",
            self._should_continue_after_analysis, 
            {
                "continue": "save_results",
                "error": "handle_error"
            }
        )
        
        # Final nodes go to END
        graph.add_edge("save_results", END)
        graph.add_edge("handle_error", END)
        
        # Compile without checkpointing to avoid serialization issues
        # Non-serializable objects (SQLAlchemy sessions) will be passed via state
        return graph.compile()
    
    def _should_continue_after_validation(self, state: PDFEvaluationState) -> str:
        """Decision point after PDF validation"""
        if state["phase"] == ProcessingPhase.ERROR:
            logger.warning("🔄 Validation failed, routing to error handler")
            return "error"
        return "continue"
    
    def _should_continue_after_extraction(self, state: PDFEvaluationState) -> str:
        """Decision point after vision extraction"""
        if state["phase"] == ProcessingPhase.ERROR:
            logger.warning("🔄 Extraction failed, routing to error handler")
            return "error"
        
        # Check if we have questions to analyze
        if not state.get("questions") or len(state["questions"]) == 0:
            logger.warning("🔄 No questions found, routing to error handler")
            state["errors"].append("No questions found in PDF")
            state["phase"] = ProcessingPhase.ERROR
            return "error"
        
        return "continue"
    
    def _should_continue_after_analysis(self, state: PDFEvaluationState) -> str:
        """Decision point after dimensional analysis"""
        if state["phase"] == ProcessingPhase.ERROR:
            logger.warning("🔄 Analysis failed, routing to error handler")
            return "error"
        
        # Even if some evaluations failed, continue if we have at least one
        if not state.get("evaluations") or len(state["evaluations"]) == 0:
            logger.warning("🔄 No evaluations completed, routing to error handler")
            state["errors"].append("No evaluations completed successfully")
            state["phase"] = ProcessingPhase.ERROR
            return "error"
        
        return "continue"
    
    async def run_evaluation(self, 
                           answer_id: int,
                           file_path: str,
                           content: str,
                           db_session: Session,
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Main entry point for PDF evaluation
        Maintains full compatibility with existing system
        
        Args:
            answer_id: Database answer ID
            file_path: Path to PDF file
            content: Text content (fallback)
            db_session: Database session
            progress_callback: WebSocket progress callback
        
        Returns:
            Dict compatible with existing comprehensive_pdf_evaluation system
        """
        
        start_time = datetime.now()
        thread_id = f"pdf_eval_{answer_id}_{int(start_time.timestamp())}"
        
        logger.info(f"🚀 Starting LangGraph PDF evaluation for answer {answer_id}")
        logger.info(f"📁 File: {file_path}")
        logger.info(f"🔗 Thread ID: {thread_id}")
        
        try:
            # Initialize state
            initial_state = PDFEvaluationState(
                # Input parameters
                answer_id=answer_id,
                file_path=file_path,
                content=content,
                db_session=db_session,
                
                # Processing state
                phase=ProcessingPhase.INITIALIZING,
                progress=0.0,
                errors=[],
                warnings=[],
                
                # PDF processing results
                total_pages=None,
                pdf_filename=None,
                extraction_successful=False,
                
                # Question data
                questions=[],
                total_questions=0,
                total_marks=0,
                
                # Analysis results
                evaluations=[],
                total_score=0.0,
                total_max_score=0.0,
                
                # Progress tracking
                progress_updates=[],
                processing_start_time=start_time.isoformat(),
                processing_end_time=None,
                
                # Callbacks
                progress_callback=progress_callback,
                
                # Final results
                final_result=None,
                evaluation_created=False,
                
                # Fallback
                fallback_data=None
            )
            
            # Execute workflow
            logger.info("🔄 Executing LangGraph workflow...")
            
            config = {"configurable": {"thread_id": thread_id}}
            
            final_state = await self.graph.ainvoke(
                initial_state,
                config=config
            )
            
            # Extract results
            result = final_state.get("final_result", {})
            
            # Add workflow metadata
            result["workflow_metadata"] = {
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "thread_id": thread_id,
                "langgraph_version": True,
                "nodes_executed": self._count_executed_nodes(final_state),
                "final_phase": final_state["phase"],
                "total_errors": len(final_state.get("errors", [])),
                "total_warnings": len(final_state.get("warnings", []))
            }
            
            logger.info(f"✅ LangGraph evaluation completed in {result['workflow_metadata']['execution_time']:.2f}s")
            logger.info(f"📊 Final score: {result.get('total_score', 0):.1f}/{result.get('total_max_score', 0):.1f}")
            logger.info(f"🔍 Questions processed: {result.get('total_questions_evaluated', 0)}")
            
            return result
            
        except Exception as e:
            error_msg = f"LangGraph workflow failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Return compatible error response
            return {
                "success": False,
                "error": error_msg,
                "workflow_metadata": {
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                    "thread_id": thread_id,
                    "langgraph_version": True,
                    "fatal_error": True
                }
            }
    
    def _count_executed_nodes(self, final_state: PDFEvaluationState) -> Dict[str, bool]:
        """Count which nodes were executed based on final state"""
        return {
            "validate_pdf": final_state.get("pdf_filename") is not None,
            "extract_vision": len(final_state.get("questions", [])) > 0,
            "analyze_dimensions": len(final_state.get("evaluations", [])) > 0,
            "save_results": final_state.get("evaluation_created", False),
            "handle_error": final_state["phase"] == ProcessingPhase.ERROR
        }
    
    async def get_workflow_state(self, thread_id: str) -> Optional[PDFEvaluationState]:
        """Get current workflow state for monitoring"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await self.graph.aget_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Failed to get workflow state: {e}")
            return None
    
    def visualize_workflow(self) -> str:
        """Get workflow visualization (for debugging)"""
        try:
            # This would generate a mermaid diagram of the workflow
            return """
            graph TD
                A[validate_pdf] --> B[extract_vision]
                B --> C[analyze_dimensions] 
                C --> D[save_results]
                A --> E[handle_error]
                B --> E
                C --> E
                D --> F[END]
                E --> F
            """
        except Exception as e:
            return f"Visualization error: {e}"
    
    async def run(self, state: PDFEvaluationState, db_session=None, progress_callback=None) -> PDFEvaluationState:
        """Execute workflow with LangGraph state"""
        thread_id = f"pdf_eval_{state['answer_id']}_{int(datetime.now().timestamp())}"
        
        # Disable checkpointing entirely to avoid serialization issues
        # LangGraph will run in stateless mode without persistence
        
        # Add non-serializable objects to state for execution
        temp_state = state.copy()
        temp_state["db_session"] = db_session
        temp_state["progress_callback"] = progress_callback
        
        # Execute workflow without checkpointing (stateless execution)
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await self.workflow.ainvoke(temp_state, config=config)
        
        # Remove non-serializable objects from final state
        if "db_session" in final_state:
            del final_state["db_session"]
        if "progress_callback" in final_state:
            del final_state["progress_callback"]
        
        return final_state

# Global workflow instance (singleton pattern for compatibility)
_pdf_workflow_instance: Optional[PDFEvaluationWorkflow] = None

def get_pdf_evaluation_workflow() -> PDFEvaluationWorkflow:
    """Get global workflow instance"""
    global _pdf_workflow_instance
    if _pdf_workflow_instance is None:
        _pdf_workflow_instance = PDFEvaluationWorkflow()
    return _pdf_workflow_instance

# Compatibility function for existing system
async def langgraph_comprehensive_pdf_evaluation(
    answer_id: int,
    file_path: str,
    content: str,
    db_session: Session,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    LangGraph-powered comprehensive PDF evaluation
    Drop-in replacement for existing comprehensive_pdf_evaluation function
    
    Maintains full API compatibility while providing advanced workflow orchestration
    """
    
    workflow = get_pdf_evaluation_workflow()
    return await workflow.run_evaluation(
        answer_id=answer_id,
        file_path=file_path,
        content=content,
        db_session=db_session,
        progress_callback=progress_callback
    )
