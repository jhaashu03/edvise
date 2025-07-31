from pydantic import BaseModel
from typing import List, Optional
from app.models.pyq import DifficultyLevel

class PYQBase(BaseModel):
    question: str
    year: int
    paper: str
    subject: str
    topic: Optional[str] = None
    marks: int
    difficulty: DifficultyLevel = DifficultyLevel.medium

class PYQCreate(PYQBase):
    pass

class PYQUpdate(BaseModel):
    question: Optional[str] = None
    year: Optional[int] = None
    paper: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    marks: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None

class PYQ(PYQBase):
    id: int
    embedding_id: Optional[str] = None

    class Config:
        from_attributes = True

class PYQSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    page: Optional[int] = 1
    subject: Optional[str] = None
    year: Optional[int] = None
    difficulty: Optional[str] = None

class PYQSearchResult(BaseModel):
    id: int
    question: str
    subject: str
    year: int
    paper: str
    topics: List[str] = []
    difficulty: str
    marks: int
    similarity_score: float

class PaginatedPYQSearchResponse(BaseModel):
    results: List[PYQSearchResult]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool
