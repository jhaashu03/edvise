from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.models.user import User
from app.models.chat import ChatMessage as ChatMessageModel, MessageRole
from app.api.api_v1.endpoints.auth import get_current_user
from app.core.llm_service import get_llm_service, LLMService, LLMServiceError
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str

@router.post("/", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Send a chat message to the AI assistant using openai
    """
    try:
        # Save user message to database
        user_message = ChatMessageModel(
            user_id=current_user.id,
            role=MessageRole.user,
            content=request.message
        )
        db.add(user_message)
        db.commit()
        
        # Prepare system prompt for UPSC assistance
        system_prompt = """You are PrepGenie, an expert AI personal assistant specializing in UPSC (Union Public Service Commission) exam preparation for Indian Civil Services. You are highly knowledgeable about Indian constitutional law, governance, history, and current affairs.

CONSTITUTIONAL LAW & POLITY:
- Indian Constitution: Features, articles, schedules, amendments
- Fundamental Rights (Articles 12-35) and Duties (Article 51A)
- Directive Principles of State Policy (Articles 36-51)
- Constitutional bodies: President, Parliament, Supreme Court, High Courts, CAG, Election Commission
- Judicial doctrines: Basic Structure Doctrine, Separation of Powers, Rule of Law, Judicial Review
- Parliamentary system, federalism, emergency provisions
- Landmark Supreme Court cases: Kesavananda Bharati (1973), Golak Nath (1967), Maneka Gandhi (1978)

INDIAN GOVERNANCE:
- Union-State relations, Centre-State disputes
- Administrative reforms, civil services, bureaucracy
- Public policy, governance innovations
- Local governance: Panchayati Raj, urban local bodies

HISTORY, GEOGRAPHY & CURRENT AFFAIRS:
- Ancient, Medieval, Modern Indian History
- Freedom movement, constitutional development
- Indian Geography, environment, climate change
- Current national and international affairs
- Economic development, social issues

EXAM GUIDANCE:
- Provide structured, comprehensive answers suitable for UPSC Mains and Prelims
- Include relevant examples, case studies, and current developments
- Connect theoretical concepts with practical applications
- Suggest further reading when appropriate
- Make this exam preparartion fun and easy for the aspirants.

Always provide accurate, well-structured answers relevant to UPSC Civil Services examination. Focus on Indian context, governance, and constitutional law. Be encouraging and supportive in your tone."""

        # Get AI response using Ollama LLM Service
        ai_response_content = await llm_service.simple_chat(
            user_message=request.message,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000
        )

        print("--------------------------")
        print(system_prompt)
        
        # Save AI response to database
        ai_message = ChatMessageModel(
            user_id=current_user.id,
            role=MessageRole.assistant,
            content=ai_response_content
        )
        db.add(ai_message)
        db.commit()
        
        # Return response in the expected format
        return ChatResponse(
            id=str(ai_message.id),
            role="assistant",
            content=ai_response_content,
            timestamp=ai_message.timestamp.isoformat()
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error for user {current_user.id}: {e}")
        db.rollback()
        
        # Return a fallback response
        fallback_response = f"I apologize, but I'm having trouble connecting to the AI service right now. Error: {str(e)}. Please try again in a moment."
        
        # Try to save fallback response to database
        try:
            ai_message = ChatMessageModel(
                user_id=current_user.id,
                role=MessageRole.assistant,
                content=fallback_response
            )
            db.add(ai_message)
            db.commit()
            
            return ChatResponse(
                id=str(ai_message.id),
                role="assistant", 
                content=fallback_response,
                timestamp=datetime.now().isoformat()
            )
        except:
            # If database save fails too, return response without saving
            return ChatResponse(
                id=str(uuid.uuid4()),
                role="assistant",
                content=fallback_response,
                timestamp=datetime.now().isoformat()
            )
        
    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {e}")
        db.rollback()
        
        # Return a fallback response
        fallback_response = "I apologize, but I'm experiencing some technical difficulties right now. Please try again in a moment. If you have specific UPSC-related questions, I'll do my best to help once the issue is resolved."
        
        # Try to save fallback response to database
        try:
            ai_message = ChatMessageModel(
                user_id=current_user.id,
                role=MessageRole.assistant,
                content=fallback_response
            )
            db.add(ai_message)
            db.commit()
            
            return ChatResponse(
                id=str(ai_message.id),
                role="assistant", 
                content=fallback_response,
                timestamp=datetime.now().isoformat()
            )
        except:
            # If database save fails too, return response without saving
            return ChatResponse(
                id=str(uuid.uuid4()),
                role="assistant",
                content=fallback_response,
                timestamp=datetime.now().isoformat()
            )

@router.get("/history")
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get chat history for the current user"""
    try:
        messages = db.query(ChatMessageModel)\
            .filter(ChatMessageModel.user_id == current_user.id)\
            .order_by(ChatMessageModel.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            ChatResponse(
                id=str(msg.id),
                role=msg.role.value,
                content=msg.content,
                timestamp=msg.timestamp.isoformat()
            )
            for msg in reversed(messages)  # Reverse to get chronological order
        ]
    except Exception as e:
        logger.error(f"Error fetching chat history for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch chat history")
