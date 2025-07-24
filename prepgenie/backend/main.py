from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.api.api_v1.api import api_router
from app.db.database import engine
from app.db.base import Base
from app.services.vector_service import vector_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    
    # Create database tables (with proper timeout handling)
    try:
        import asyncio
        import concurrent.futures
        import threading
        
        def create_tables():
            Base.metadata.create_all(bind=engine)
            return True
        
        # Use ThreadPoolExecutor with timeout for database operations
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(create_tables)
            try:
                # Wait for completion with 10 second timeout
                future.result(timeout=10)
                logger.info("Database tables created successfully")
            except concurrent.futures.TimeoutError:
                logger.warning("Database table creation timed out, continuing startup...")
            except Exception as e:
                logger.error(f"Failed to create database tables: {e}")
                raise
                
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        logger.info("Continuing startup without database connection...")
    
    # Initialize vector service connection (with timeout) - only if not disabled
    if not getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
        try:
            import asyncio
            await asyncio.wait_for(vector_service.connect(), timeout=10.0)
            logger.info("Vector service connected successfully")
        except asyncio.TimeoutError:
            logger.warning("Vector service connection timed out, continuing startup...")
        except Exception as e:
            logger.error(f"Failed to connect to vector service: {e}")
    else:
        logger.info("Vector service is disabled, skipping connection")
        # Continue startup even if vector service fails to connect
        # The endpoints will handle connection retries
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Disconnect from vector service
    try:
        await vector_service.disconnect()
        logger.info("Vector service disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting vector service: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PrepGenie API - Your Personalized UPSC AI Mentor",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with user-friendly messages"""
    logger.error(f"Validation error: {exc}")
    
    # Extract first error message
    first_error = exc.errors()[0] if exc.errors() else None
    
    if first_error:
        field = first_error.get('loc', ['unknown'])[-1]  # Get the field name
        msg = first_error.get('msg', 'Invalid input')
        
        # Provide user-friendly error messages
        if 'email' in str(field).lower():
            user_message = "Please enter a valid email address"
        elif 'password' in str(field).lower():
            user_message = "Password is required"
        else:
            user_message = f"Invalid {field}: {msg}"
    else:
        user_message = "Please check your input and try again"
    
    return JSONResponse(
        status_code=400,
        content={
            "detail": user_message,
            "type": "validation_error"
        }
    )

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "PrepGenie API - Your Personalized UPSC AI Mentor"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
