from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.answer import UploadedAnswer, AnswerEvaluation
from app.schemas.answer import AnswerCreate, AnswerEvaluationCreate


def create_answer(db: Session, answer: AnswerCreate, user_id: int) -> UploadedAnswer:
    """Create a new uploaded answer"""
    db_answer = UploadedAnswer(
        user_id=user_id,
        question_id=answer.question_id,
        content=answer.content,
        file_path=answer.file_path
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    return db_answer


def get_answer(db: Session, answer_id: int) -> Optional[UploadedAnswer]:
    """Get a specific answer by ID"""
    return db.query(UploadedAnswer).filter(UploadedAnswer.id == answer_id).first()


def get_user_answers(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[UploadedAnswer]:
    """Get all answers by a specific user"""
    return db.query(UploadedAnswer).filter(
        UploadedAnswer.user_id == user_id
    ).offset(skip).limit(limit).all()


def get_answers(db: Session, skip: int = 0, limit: int = 100) -> List[UploadedAnswer]:
    """Get all answers with pagination"""
    return db.query(UploadedAnswer).offset(skip).limit(limit).all()


def update_answer(db: Session, answer_id: int, content: str) -> Optional[UploadedAnswer]:
    """Update answer content"""
    db_answer = db.query(UploadedAnswer).filter(UploadedAnswer.id == answer_id).first()
    if db_answer:
        db_answer.content = content
        db.commit()
        db.refresh(db_answer)
    return db_answer


def delete_answer(db: Session, answer_id: int) -> bool:
    """Delete an answer"""
    db_answer = db.query(UploadedAnswer).filter(UploadedAnswer.id == answer_id).first()
    if db_answer:
        db.delete(db_answer)
        db.commit()
        return True
    return False


def create_answer_evaluation(db: Session, evaluation: AnswerEvaluationCreate, answer_id: int) -> AnswerEvaluation:
    """Create an evaluation for an answer"""
    db_evaluation = AnswerEvaluation(
        answer_id=answer_id,
        score=evaluation.score,
        max_score=evaluation.max_score,
        feedback=evaluation.feedback,
        strengths=evaluation.strengths,
        improvements=evaluation.improvements,
        structure=evaluation.structure,
        coverage=evaluation.coverage,
        tone=evaluation.tone,
        actionable_data=evaluation.actionable_data  # Store full actionable evaluation data
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation


def get_answer_evaluation(db: Session, answer_id: int) -> Optional[AnswerEvaluation]:
    """Get evaluation for a specific answer"""
    return db.query(AnswerEvaluation).filter(AnswerEvaluation.answer_id == answer_id).first()


def update_answer_evaluation(db: Session, evaluation_id: int, **kwargs) -> Optional[AnswerEvaluation]:
    """Update an answer evaluation"""
    db_evaluation = db.query(AnswerEvaluation).filter(AnswerEvaluation.id == evaluation_id).first()
    if db_evaluation:
        for key, value in kwargs.items():
            if hasattr(db_evaluation, key):
                setattr(db_evaluation, key, value)
        db.commit()
        db.refresh(db_evaluation)
    return db_evaluation
