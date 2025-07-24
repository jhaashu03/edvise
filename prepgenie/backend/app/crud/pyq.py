from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.pyq import PYQ
from app.schemas.pyq import PYQCreate, PYQUpdate

def get_pyq(db: Session, pyq_id: int) -> Optional[PYQ]:
    return db.query(PYQ).filter(PYQ.id == pyq_id).first()

def get_pyqs(db: Session, skip: int = 0, limit: int = 100) -> List[PYQ]:
    return db.query(PYQ).offset(skip).limit(limit).all()

def get_pyqs_by_subject(db: Session, subject: str, skip: int = 0, limit: int = 100) -> List[PYQ]:
    return db.query(PYQ).filter(PYQ.subject == subject).offset(skip).limit(limit).all()

def get_pyqs_by_year(db: Session, year: int, skip: int = 0, limit: int = 100) -> List[PYQ]:
    return db.query(PYQ).filter(PYQ.year == year).offset(skip).limit(limit).all()

def create_pyq(db: Session, pyq: PYQCreate) -> PYQ:
    db_pyq = PYQ(**pyq.dict())
    db.add(db_pyq)
    db.commit()
    db.refresh(db_pyq)
    return db_pyq

def update_pyq(db: Session, pyq_id: int, pyq_update: PYQUpdate) -> Optional[PYQ]:
    db_pyq = db.query(PYQ).filter(PYQ.id == pyq_id).first()
    if db_pyq:
        update_data = pyq_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_pyq, field, value)
        db.commit()
        db.refresh(db_pyq)
    return db_pyq

def update_pyq_embedding_id(db: Session, pyq_id: int, embedding_id: str) -> Optional[PYQ]:
    db_pyq = db.query(PYQ).filter(PYQ.id == pyq_id).first()
    if db_pyq:
        db_pyq.embedding_id = embedding_id
        db.commit()
        db.refresh(db_pyq)
    return db_pyq

def delete_pyq(db: Session, pyq_id: int) -> bool:
    db_pyq = db.query(PYQ).filter(PYQ.id == pyq_id).first()
    if db_pyq:
        db.delete(db_pyq)
        db.commit()
        return True
    return False
