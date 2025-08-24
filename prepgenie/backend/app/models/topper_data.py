"""
Topper Data Models
Data structures for storing extracted topper information and content
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TopperPageType(str, Enum):
    """Types of pages in topper PDFs"""
    GENERAL_INFO = "general_info"
    CANDIDATE_INFO = "candidate_info" 
    INSTRUCTIONS = "instructions"
    QUESTION_ANSWER = "question_answer"
    OTHER = "other"

class TopperPageContent(BaseModel):
    """Content extracted from a single page"""
    page_number: int
    page_type: TopperPageType
    raw_text: str
    vision_analysis: Dict[str, Any] = Field(default_factory=dict)
    questions_found: List[Dict[str, Any]] = Field(default_factory=list)
    answers_found: List[Dict[str, Any]] = Field(default_factory=list)
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    confidence_score: float = 0.0
    
class TopperInfo(BaseModel):
    """Parsed topper information from PDF filename and content"""
    institute: str
    topper_name: str
    exam_year: int
    rank: Optional[int] = None
    
    # Additional info that might be extracted from content
    full_name: Optional[str] = None
    roll_number: Optional[str] = None
    category: Optional[str] = None
    optional_subject: Optional[str] = None
    
class TopperQuestionAnswer(BaseModel):
    """Individual question-answer pair from topper"""
    question_id: str  # Unique identifier
    question_number: int
    question_text: str
    answer_text: str
    marks_allocated: Optional[int] = None
    word_count: int = 0
    page_numbers: List[int] = Field(default_factory=list)
    subject: Optional[str] = None
    topic: Optional[str] = None
    answer_quality: Optional[str] = None  # excellent, good, average
    
class TopperDocument(BaseModel):
    """Complete topper document with all extracted content"""
    document_id: str  # Unique identifier
    file_path: str
    filename: str
    
    # Topper information
    topper_info: TopperInfo
    
    # Document metadata
    total_pages: int
    file_size_mb: float
    processing_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Extracted content
    pages: List[TopperPageContent] = Field(default_factory=list)
    question_answers: List[TopperQuestionAnswer] = Field(default_factory=list)
    
    # Processing statistics
    processing_stats: Dict[str, Any] = Field(default_factory=dict)
    extraction_successful: bool = False
    error_log: List[str] = Field(default_factory=list)
    
    def get_qa_count(self) -> int:
        """Get total number of question-answer pairs"""
        return len(self.question_answers)
    
    def get_total_word_count(self) -> int:
        """Get total word count across all answers"""
        return sum(qa.word_count for qa in self.question_answers)
    
    def get_pages_by_type(self, page_type: TopperPageType) -> List[TopperPageContent]:
        """Get pages of a specific type"""
        return [page for page in self.pages if page.page_type == page_type]

class TopperExtractionBatch(BaseModel):
    """Batch processing results for multiple topper PDFs"""
    batch_id: str
    processing_started: datetime = Field(default_factory=datetime.now)
    processing_completed: Optional[datetime] = None
    
    # Input parameters
    source_directories: List[str] = Field(default_factory=list)
    total_files_found: int = 0
    
    # Processing results
    documents: List[TopperDocument] = Field(default_factory=list)
    successful_extractions: int = 0
    failed_extractions: int = 0
    
    # Summary statistics
    total_pages_processed: int = 0
    total_qa_pairs: int = 0
    total_word_count: int = 0
    
    def add_document(self, document: TopperDocument):
        """Add a processed document to the batch"""
        self.documents.append(document)
        if document.extraction_successful:
            self.successful_extractions += 1
            self.total_qa_pairs += document.get_qa_count()
            self.total_word_count += document.get_total_word_count()
        else:
            self.failed_extractions += 1
        
        self.total_pages_processed += document.total_pages
    
    def complete_batch(self):
        """Mark batch as completed"""
        self.processing_completed = datetime.now()
    
    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if self.processing_completed:
            return (self.processing_completed - self.processing_started).total_seconds()
        return None

class TopperEmbeddingEntry(BaseModel):
    """Entry for storing in vector database with BGE embeddings"""
    topper_id: str
    topper_name: str
    institute: str
    rank: Optional[int]
    exam_year: int
    
    question_id: str
    question_text: str
    subject: Optional[str]
    topic: Optional[str]
    marks: Optional[int]
    
    answer_text: str
    word_count: int
    
    source_document: str
    page_number: int
    
    embedding: List[float]  # BGE model embedding (1024 dimensions)
    
    created_at: datetime = Field(default_factory=datetime.now)
