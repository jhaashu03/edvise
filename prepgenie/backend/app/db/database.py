from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure engine with database-specific optimizations
if "sqlite" in settings.DATABASE_URL.lower():
    # SQLite configuration - no pooling parameters
    engine_kwargs = {
        "connect_args": {"check_same_thread": False}
    }
else:
    # PostgreSQL/Supabase configuration
    engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 3,  # Timeout after 3 seconds waiting for connection from pool
    }
    
    # SSL configuration and connection timeout for Supabase
    if "supabase" in settings.DB_HOST:
        engine_kwargs["connect_args"] = {
            "sslmode": "require",
            "connect_timeout": 3,  # Timeout after 3 seconds trying to connect
            "application_name": "PrepGenie-API",
        }
    else:
        engine_kwargs["connect_args"] = {
            "connect_timeout": 3,  # Timeout after 3 seconds trying to connect
        }

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_db_connection():
    """Test database connection quickly"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        # Quick connection test with timeout
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        db.close()
        return True
    except Exception:
        return False
