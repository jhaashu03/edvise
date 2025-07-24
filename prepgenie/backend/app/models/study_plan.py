from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

class StudyTargetStatus(enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class StudyTargetPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    targets = relationship("StudyTarget", back_populates="study_plan")
    user = relationship("User")

class StudyTarget(Base):
    __tablename__ = "study_targets"

    id = Column(Integer, primary_key=True, index=True)
    study_plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(StudyTargetStatus), default=StudyTargetStatus.pending)
    priority = Column(Enum(StudyTargetPriority), default=StudyTargetPriority.medium)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    study_plan = relationship("StudyPlan", back_populates="targets")
