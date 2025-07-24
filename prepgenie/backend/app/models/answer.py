from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class UploadedAnswer(Base):
    __tablename__ = "uploaded_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(String, nullable=False)  # Reference to PYQ or custom question
    content = Column(Text, nullable=True)  # Made nullable for PDF uploads
    file_path = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    evaluation = relationship("AnswerEvaluation", back_populates="answer", uselist=False)

class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("uploaded_answers.id"), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False, default=100.0)
    feedback = Column(Text, nullable=False)
    strengths = Column(Text, nullable=True)  # JSON string
    improvements = Column(Text, nullable=True)  # JSON string
    structure = Column(Float, nullable=False, default=0.0)
    coverage = Column(Float, nullable=False, default=0.0)
    tone = Column(Float, nullable=False, default=0.0)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    answer = relationship("UploadedAnswer", back_populates="evaluation")
