from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnswerBase(BaseModel):
    question_id: str
    content: Optional[str] = None
    file_path: Optional[str] = None


class AnswerCreate(AnswerBase):
    pass


class AnswerUpdate(BaseModel):
    content: Optional[str] = None
    file_path: Optional[str] = None


class AnswerEvaluationBase(BaseModel):
    score: float
    max_score: float = 100.0
    feedback: str
    strengths: Optional[str] = None  # JSON string
    improvements: Optional[str] = None  # JSON string
    structure: float = 0.0
    coverage: float = 0.0
    tone: float = 0.0


class AnswerEvaluationCreate(AnswerEvaluationBase):
    pass


class AnswerEvaluationUpdate(BaseModel):
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    structure: Optional[float] = None
    coverage: Optional[float] = None
    tone: Optional[float] = None


class AnswerEvaluation(AnswerEvaluationBase):
    id: int
    answer_id: int
    evaluated_at: str = Field(..., description="ISO formatted date string")
    # These match the database schema (JSON strings)
    strengths: Optional[str] = None
    improvements: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Response schema for API endpoints that need parsed arrays
class AnswerEvaluationSchema(BaseModel):
    id: int
    answer_id: int = Field(..., alias="answerId")
    score: float
    max_score: float = Field(100.0, alias="maxScore")
    feedback: str
    strengths: Optional[List[str]] = None  # Parsed to list for frontend
    improvements: Optional[List[str]] = None  # Parsed to list for frontend
    structure: float = 0.0
    coverage: float = 0.0
    tone: float = 0.0
    evaluated_at: str = Field(..., alias="evaluatedAt", description="ISO formatted date string")

    @classmethod
    def parse_json_list(cls, v):
        """Parse JSON string to list if needed"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                import json
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat as single item
                return [v] if v else []
        return [str(v)] if v else []

    @classmethod
    def __init_subclass__(cls, **kwargs):
        # Add validators for strengths and improvements
        super().__init_subclass__(**kwargs)
        
    def __init__(self, **data):
        # Parse strengths and improvements before validation
        if 'strengths' in data:
            data['strengths'] = self.parse_json_list(data['strengths'])
        if 'improvements' in data:
            data['improvements'] = self.parse_json_list(data['improvements'])
        super().__init__(**data)

    class Config:
        from_attributes = True
        populate_by_name = True


class Answer(AnswerBase):
    id: int
    user_id: int
    uploaded_at: datetime
    evaluation: Optional[AnswerEvaluation] = None

    class Config:
        from_attributes = True


# Response models
class AnswerResponse(BaseModel):
    id: int
    question_id: str = Field(..., alias="questionId")
    content: str
    file_path: Optional[str] = Field(None, alias="filePath")
    file_name: Optional[str] = Field(None, alias="fileName")
    uploaded_at: str = Field(..., alias="uploadedAt", description="ISO formatted date string")
    evaluation: Optional[AnswerEvaluationSchema] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AnswerUploadResponse(BaseModel):
    id: int
    message: str
    answer: AnswerResponse
    task_id: Optional[str] = None
    processing_started: Optional[bool] = False
