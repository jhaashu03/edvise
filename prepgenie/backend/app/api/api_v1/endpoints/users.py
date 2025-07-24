from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.api.api_v1.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user
