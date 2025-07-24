from sqlalchemy import Column, Integer, String, Text, Enum
from app.db.database import Base
import enum

class ImportanceLevel(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class SyllabusItem(Base):
    __tablename__ = "syllabus_items"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    subtopics = Column(Text, nullable=True)  # JSON string
    paper = Column(String, nullable=False)
    importance = Column(Enum(ImportanceLevel), default=ImportanceLevel.medium)
