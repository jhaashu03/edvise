"""
Workflow Configuration for PDF Evaluation
Controls which evaluation system to use (legacy vs LangGraph)
"""

import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)

class WorkflowConfig:
    """Configuration for PDF evaluation workflows"""
    
    # Workflow selection
    EVALUATION_MODE: Literal["legacy", "langgraph", "hybrid"] = os.getenv("EVALUATION_MODE", "langgraph")
    
    # LangGraph specific settings
    LANGGRAPH_TIMEOUT = int(os.getenv("LANGGRAPH_TIMEOUT", "900"))  # 15 minutes
    LANGGRAPH_MAX_RETRIES = int(os.getenv("LANGGRAPH_MAX_RETRIES", "3"))
    
    # A/B Testing (user-based routing)
    LANGGRAPH_USER_PERCENTAGE = float(os.getenv("LANGGRAPH_USER_PERCENTAGE", "0.0"))  # 0% = disabled
    
    # Feature flags
    ENABLE_WORKFLOW_MONITORING = os.getenv("ENABLE_WORKFLOW_MONITORING", "true").lower() == "true"
    ENABLE_PROGRESS_STREAMING = os.getenv("ENABLE_PROGRESS_STREAMING", "true").lower() == "true"
    
    @classmethod
    def should_use_langgraph(cls, user_id: int = None, force_mode: str = None) -> bool:
        """
        Determine whether to use LangGraph workflow for this request
        
        Args:
            user_id: User ID for A/B testing (optional)
            force_mode: Override mode (legacy/langgraph)
            
        Returns:
            True if LangGraph should be used, False for legacy
        """
        
        # Force mode override (for testing/debugging)
        if force_mode:
            result = force_mode.lower() == "langgraph"
            logger.info(f"🔧 Workflow forced to: {'LangGraph' if result else 'Legacy'}")
            return result
        
        # Check if LangGraph is available
        try:
            from app.workflows import langgraph_comprehensive_pdf_evaluation
            langgraph_available = True
        except ImportError:
            langgraph_available = False
            logger.warning("⚠️ LangGraph not available, using legacy workflow")
            return False
        
        # Mode-based decision
        if cls.EVALUATION_MODE == "langgraph":
            logger.info("🚀 Using LangGraph workflow (configured mode)")
            return langgraph_available
        
        elif cls.EVALUATION_MODE == "legacy":
            logger.info("🔄 Using Legacy workflow (configured mode)")
            return False
        
        elif cls.EVALUATION_MODE == "hybrid":
            # A/B testing based on user ID
            if user_id and cls.LANGGRAPH_USER_PERCENTAGE > 0:
                # Simple hash-based distribution
                use_langgraph = (hash(str(user_id)) % 100) < (cls.LANGGRAPH_USER_PERCENTAGE * 100)
                workflow_name = "LangGraph" if use_langgraph else "Legacy"
                logger.info(f"🎯 Hybrid mode - User {user_id}: {workflow_name} ({cls.LANGGRAPH_USER_PERCENTAGE:.1%} LangGraph)")
                return use_langgraph and langgraph_available
            else:
                logger.info("🔄 Hybrid mode - No user ID or 0% LangGraph, using Legacy")
                return False
        
        # Default to legacy
        logger.info("🔄 Default to Legacy workflow")
        return False
    
    @classmethod
    def get_workflow_name(cls, user_id: int = None, force_mode: str = None) -> str:
        """Get the name of the workflow that will be used"""
        return "LangGraph" if cls.should_use_langgraph(user_id, force_mode) else "Legacy"
