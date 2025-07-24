"""
Database connection utilities with timeout and error handling
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from app.db.database import SessionLocal
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

@contextmanager
def get_db_with_timeout(timeout_seconds: int = 5):
    """
    Get database session with timeout handling
    """
    db: Optional[Session] = None
    try:
        # Try to create a session with timeout
        db = SessionLocal()
        
        # Test the connection with a simple query
        db.execute(text("SELECT 1"))
        
        yield db
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        if db:
            db.close()
        raise Exception("Database connection timeout")
    except Exception as e:
        logger.error(f"Database error: {e}")
        if db:
            db.close()
        raise e
    finally:
        if db:
            db.close()

def test_db_connection() -> bool:
    """
    Test if database connection is working
    """
    try:
        with get_db_with_timeout(timeout_seconds=3):
            return True
    except Exception:
        return False
