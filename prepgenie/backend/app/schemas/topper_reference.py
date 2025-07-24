"""
Topper Reference Schemas
Pydantic models for topper content and analysis
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TopperReferenceBase(BaseModel):
    topper_name: str
    institute: Optional[str] = None
    exam_year: Optional[int] = None
    rank: Optional[int] = None
    question_id: str
    question_text: str
    subject: str
    topic: Optional[str] = None
    marks: int
    topper_answer_text: str
    word_count: Optional[int] = None

class TopperReferenceCreate(TopperReferenceBase):
    answer_analysis: Optional[Dict[str, Any]] = None
    writing_patterns: Optional[Dict[str, Any]] = None
    source_document: Optional[str] = None
    page_number: Optional[int] = None

class TopperReference(TopperReferenceBase):
    id: int
    answer_analysis: Optional[Dict[str, Any]] = None
    writing_patterns: Optional[Dict[str, Any]] = None
    source_document: Optional[str] = None
    page_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TopperPatternBase(BaseModel):
    pattern_type: str
    pattern_name: str
    description: str

class TopperPatternCreate(TopperPatternBase):
    subjects: Optional[List[str]] = None
    question_types: Optional[List[str]] = None
    frequency: Optional[float] = None
    effectiveness_score: Optional[float] = None
    examples: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[int]] = None

class TopperPattern(TopperPatternBase):
    id: int
    subjects: Optional[List[str]] = None
    question_types: Optional[List[str]] = None
    frequency: Optional[float] = None
    effectiveness_score: Optional[float] = None
    examples: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[int]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Analysis comparison results
class TopperComparisonResult(BaseModel):
    """Result of comparing student answer with topper patterns"""
    
    # Overall comparison
    similarity_score: float  # 0-10 scale
    topper_reference_id: Optional[int] = None
    topper_name: Optional[str] = None
    
    # Specific comparisons
    structure_comparison: Dict[str, Any]
    content_approach_comparison: Dict[str, Any]
    writing_style_comparison: Dict[str, Any]
    example_usage_comparison: Dict[str, Any]
    
    # Topper insights and recommendations
    topper_strengths_identified: List[str]
    missing_topper_techniques: List[str]
    specific_improvements: List[str]
    topper_inspired_suggestions: List[str]

class TopperAnalysisDimension(BaseModel):
    """14th Dimension: Topper Analysis Comparison"""
    
    score: str  # "X/10" format
    feedback: str
    
    # Detailed comparison results
    comparison_result: TopperComparisonResult
    
    # Actionable insights
    topper_techniques_to_adopt: List[str]
    specific_examples_to_study: List[str]
    writing_patterns_to_emulate: List[str]
    structural_improvements: List[str]
