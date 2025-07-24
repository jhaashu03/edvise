# Import all the models to register them with SQLAlchemy
from app.db.database import Base
from app.models.user import User
from app.models.study_plan import StudyPlan, StudyTarget
from app.models.answer import UploadedAnswer, AnswerEvaluation
from app.models.pyq import PYQ
from app.models.syllabus import SyllabusItem
from app.models.chat import ChatMessage
from app.models.topper_reference import TopperReference, TopperPattern

__all__ = ["Base"]
