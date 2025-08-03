"""
LangGraph State Definitions for PDF Evaluation Workflow
Maintains compatibility with existing system while adding workflow orchestration
"""

from typing import List, Dict, Any, Optional, TypedDict, Annotated
from enum import Enum
import operator

class ProcessingPhase(str, Enum):
    """Processing phases for progress tracking"""
    INITIALIZING = "initializing"
    PDF_VALIDATION = "pdf_validation"
    VISION_EXTRACTION = "vision_extraction"
    QUESTION_MATCHING = "question_matching"
    DIMENSIONAL_ANALYSIS = "dimensional_analysis"
    TOPPER_COMPARISON = "topper_comparison"
    SCORE_CALCULATION = "score_calculation"
    DATABASE_STORAGE = "database_storage"
    COMPLETED = "completed"
    ERROR = "error"

class QuestionData(TypedDict):
    """Individual question data structure"""
    question_number: int
    question_text: str
    student_answer: str
    marks: int
    page_number: int
    word_limit: Optional[int]
    time_limit: Optional[int]

class EvaluationResult(TypedDict):
    """Evaluation result for a single question"""
    question_number: int
    question_text: str
    current_score: float
    max_score: float
    detailed_feedback: Dict[str, Any]
    strengths: List[str]
    improvements: List[str]
    topper_comparison: Optional[Dict[str, Any]]
    processing_time: float

class ProgressUpdate(TypedDict):
    """Progress update structure for WebSocket streaming"""
    phase: ProcessingPhase
    progress_percentage: float
    current_step: str
    details: str
    questions_processed: int
    total_questions: int
    estimated_time_remaining: Optional[float]
    timestamp: str

class PDFEvaluationState(TypedDict):
    """
    Central state for PDF evaluation workflow
    Compatible with existing system data structures
    """
    # Input parameters
    answer_id: int
    file_path: str
    content: str
    # Note: db_session and progress_callback moved to config to avoid serialization issues
    
    # Processing state
    phase: ProcessingPhase
    progress: float
    errors: Annotated[List[str], operator.add]  # Accumulate errors
    warnings: Annotated[List[str], operator.add]  # Accumulate warnings
    
    # PDF processing results
    total_pages: Optional[int]
    pdf_filename: Optional[str]
    extraction_successful: bool
    
    # Question data
    questions: Annotated[List[QuestionData], operator.add]  # Accumulate questions
    total_questions: int
    total_marks: int
    
    # Analysis results
    evaluations: List[EvaluationResult]  # Store evaluations (no auto-accumulation)
    total_score: float
    total_max_score: float
    
    # Progress tracking
    progress_updates: Annotated[List[ProgressUpdate], operator.add]
    processing_start_time: Optional[str]
    processing_end_time: Optional[str]
    
    # WebSocket callback for real-time updates
    progress_callback: Optional[Any]
    
    # Final results (compatible with existing system)
    final_result: Optional[Dict[str, Any]]
    evaluation_created: bool
    
    # Fallback data (for error recovery)
    fallback_data: Optional[Dict[str, Any]]

class NodeResult(TypedDict):
    """Standard result structure for workflow nodes"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    warnings: Optional[List[str]]
    processing_time: float

class WorkflowConfig(TypedDict):
    """Configuration for PDF evaluation workflow"""
    max_retries: int
    timeout_seconds: int
    enable_topper_comparison: bool
    enable_progress_streaming: bool
    fallback_on_error: bool
    detailed_logging: bool
