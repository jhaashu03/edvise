from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, users, study_plans, pyqs, answers, chat, progress, syllabus, conversation_management
from app.api import llm_endpoints, websocket_progress

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(study_plans.router, prefix="/study-plans", tags=["study-plans"])
api_router.include_router(pyqs.router, prefix="/pyqs", tags=["pyqs"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# Add conversation management endpoints
api_router.include_router(conversation_management.router, prefix="/conversation-management", tags=["conversation-management"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(syllabus.router, prefix="/syllabus", tags=["syllabus"])
# Add Ollama LLM endpoints
api_router.include_router(llm_endpoints.router, prefix="/llm", tags=["llm"])
# Add WebSocket progress tracking
api_router.include_router(websocket_progress.router, prefix="/progress", tags=["progress-websocket"])
