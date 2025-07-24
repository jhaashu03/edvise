from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta
from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, Token, UserLogin, RegistrationResponse
from app.crud.user import get_user_by_email, create_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email=email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.core.security import verify_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=RegistrationResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = get_user_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered. Please use a different email address or try logging in."
            )
        
        # Create new user
        user = create_user(db, user=user_in)
        
        return {
            "message": "Registration successful! Please log in with your credentials.",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed due to a server error. Please try again."
        )

@router.post("/login", response_model=Token)
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login user with OAuth2 form data (standard format)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate input data first
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    try:
        # OAuth2 uses 'username' field but we treat it as email
        user = authenticate_user(db, username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please check your credentials and try again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Login failed due to a server error. Please try again."
        )
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to log in at the moment. Our database connection is having issues. Please try again later."
        )

@router.get("/health")
def auth_health_check(db: Session = Depends(get_db)):
    """Check authentication service health including database connectivity"""
    try:
        # Test database connection with a simple query
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database_connected": True,
            "message": "Authentication service is running"
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "degraded",
                "database_connected": False,
                "message": "Authentication service is running but database is not accessible"
            }
        )
    
    return response

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
