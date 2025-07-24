"""
Topper Reference Content Model
Stores and manages topper answer patterns and analysis data
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class TopperReference(Base):
    __tablename__ = "topper_references"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)         # e.g., "Shakti Dubey"
    institute = Column(String, nullable=True)     # e.g., "VisionIAS"
    exam_year = Column(Integer, nullable=False)   # e.g., 2024
    rank = Column(Integer, nullable=True)         # e.g., 1, 2, 3...
    
    # File metadata
    source_file = Column(String, nullable=True)   # PDF filename
    total_questions = Column(Integer, nullable=True)
    extraction_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to answers
    answers = relationship("TopperAnswer", back_populates="topper_reference")


class TopperAnswer(Base):
    __tablename__ = "topper_answers"

    id = Column(Integer, primary_key=True, index=True)
    topper_reference_id = Column(Integer, ForeignKey("topper_references.id"), nullable=False)
    
    # Question details
    question_number = Column(String, nullable=False)  # e.g., "Q1", "Q2a"
    question_text = Column(Text, nullable=False)      # Full question text
    answer_text = Column(Text, nullable=False)        # Topper's answer
    
    # Classification
    subject = Column(String, nullable=False)          # GS-I, GS-II, GS-III, GS-IV
    topic = Column(String, nullable=True)             # Specific topic
    marks = Column(Integer, nullable=False)           # Question marks
    
    # Metadata
    word_count = Column(Integer, nullable=True)
    page_reference = Column(String, nullable=True)   # Page numbers in original
    
    # Analysis data
    writing_patterns = Column(JSON, nullable=True)   # Identified patterns
    key_techniques = Column(JSON, nullable=True)     # Techniques used
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship back to topper
    topper_reference = relationship("TopperReference", back_populates="answers")


class TopperPattern(Base):
    __tablename__ = "topper_patterns"

    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String, nullable=False)  # "structure", "examples", "approach", etc.
    pattern_name = Column(String, nullable=False)  # "Flowchart Usage", "Multiple Examples"
    description = Column(Text, nullable=False)
    
    # Pattern characteristics
    subjects = Column(JSON, nullable=True)      # Which subjects this applies to
    question_types = Column(JSON, nullable=True)  # Question types where this is effective
    frequency = Column(Float, nullable=True)    # How often toppers use this (0-1)
    effectiveness_score = Column(Float, nullable=True)  # Impact on marks (0-10)
    
    # Examples and evidence
    examples = Column(JSON, nullable=True)      # Specific examples from topper answers
    references = Column(JSON, nullable=True)   # References to TopperReference records
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
