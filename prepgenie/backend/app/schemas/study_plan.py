from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum

class StudyTargetStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class StudyTargetPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class StudyTargetBase(BaseModel):
    subject: str
    topic: str
    due_date: datetime
    status: StudyTargetStatus = StudyTargetStatus.pending
    priority: StudyTargetPriority = StudyTargetPriority.medium

class StudyTargetCreate(StudyTargetBase):
    pass

class StudyTargetUpdate(BaseModel):
    subject: Optional[str] = None
    topic: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[StudyTargetStatus] = None
    priority: Optional[StudyTargetPriority] = None

class StudyTarget(StudyTargetBase):
    id: int
    study_plan_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StudyPlanBase(BaseModel):
    target_date: datetime

class StudyPlanCreate(StudyPlanBase):
    pass

class StudyPlanUpdate(BaseModel):
    target_date: Optional[datetime] = None

class StudyPlan(StudyPlanBase):
    id: int
    user_id: int
    targets: List[StudyTarget] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
