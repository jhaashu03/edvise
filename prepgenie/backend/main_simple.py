from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PrepGenie API - Your Personalized UPSC AI Mentor",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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

# Import and include routers
try:
    from app.api.api_v1.api import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    logger.info("API routes loaded successfully")
except Exception as e:
    logger.error(f"Failed to load API routes: {e}")

@app.get("/")
async def root():
    return {"message": "PrepGenie API - Your Personalized UPSC AI Mentor"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database_configured": bool(settings.DB_HOST and settings.DB_USER and settings.DB_PASSWORD),
        "vector_service_configured": bool(settings.MILVUS_URI and settings.MILVUS_TOKEN),
        "jwt_configured": bool(settings.SECRET_KEY),
    }

@app.get("/api/v1/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "API is working!",
        "config": {
            "db_host": settings.DB_HOST,
            "db_user": settings.DB_USER,
            "project_name": settings.PROJECT_NAME
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
