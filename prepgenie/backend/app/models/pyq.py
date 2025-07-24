from sqlalchemy import Column, Integer, String, Text, Enum
from app.db.database import Base
import enum

class DifficultyLevel(enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class PYQ(Base):
    __tablename__ = "pyqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    paper = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(Text, nullable=True)  # JSON string of topics
    marks = Column(Integer, nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.medium)
    embedding_id = Column(String, nullable=True)  # Milvus vector ID
