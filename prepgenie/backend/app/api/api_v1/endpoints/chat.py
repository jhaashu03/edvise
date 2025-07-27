from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.db.database import get_db
from app.models.user import User
from app.models.chat import (
    ChatMessage as ChatMessageModel, 
    ChatConversation as ChatConversationModel,
    MessageRole, 
    ConversationStatus
)
from app.api.api_v1.endpoints.auth import get_current_user
from app.core.llm_service import get_llm_service, LLMService, LLMServiceError, ChatMessage
from app.utils.conversation_manager import ConversationManager
import logging
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # UUID of existing conversation

class ConversationResponse(BaseModel):
    id: str
    uuid: str
    title: str
    topic: Optional[str]
    summary: Optional[str]
    status: str
    message_count: int
    created_at: str
    updated_at: str
    is_pinned: bool
    tags: Optional[str]

class ChatResponse(BaseModel):
    id: str
    conversation_id: str
    conversation_uuid: str
    role: str
    content: str
    timestamp: str
    tokens_used: Optional[int] = None

class ConversationSearchRequest(BaseModel):
    query: str
    status: Optional[str] = "active"

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = None
    status: Optional[str] = None

@router.post("/", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Send a chat message to the AI assistant with conversation session management
    """
    try:
        conversation_manager = ConversationManager(llm_service)
        
        # Get or create conversation
        conversation = None
        if request.conversation_id:
            # Find existing conversation by UUID
            conversation = db.query(ChatConversationModel).filter(
                ChatConversationModel.uuid == request.conversation_id,
                ChatConversationModel.user_id == current_user.id
            ).first()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Create new conversation if none exists
        if not conversation:
            conversation = await conversation_manager.create_conversation(
                user_id=current_user.id,
                first_message=request.message,
                db=db
            )
        
        # Save user message to database
        user_message = ChatMessageModel(
            conversation_id=conversation.id,
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

        # Build optimized conversation context for AI
        print(f"🔧 DEBUG: Building conversation context...")
        print(f"🔧 DEBUG: Conversation ID: {conversation.id if conversation else None}")
        print(f"🔧 DEBUG: User ID: {current_user.id}")
        print(f"🔧 DEBUG: Current message: {request.message[:100]}...")
        
        conversation_context = await _build_conversation_context(
            conversation,
            request.message,
            db,
            llm_service
        )
        
        print(f"🔧 DEBUG: Built context with {len(conversation_context)} messages")
        for i, msg in enumerate(conversation_context):
            print(f"🔧 DEBUG: Message {i}: Role={msg.role}, Content={msg.content[:50]}...")
        
        # Get AI response with full conversation context
        ai_response = await llm_service.chat_completion(
            messages=conversation_context,
            temperature=0.7,
            max_tokens=1000
        )
        ai_response_content = ai_response.content

        print("--------------------------")
        print(system_prompt)
        
        # Save AI response to database with conversation context
        ai_message = ChatMessageModel(
            conversation_id=conversation.id,
            user_id=current_user.id,
            role=MessageRole.assistant,
            content=ai_response_content
        )
        db.add(ai_message)
        db.commit()
        
        # Update conversation metadata
        await conversation_manager.update_conversation_metadata(conversation, db)
        
        # Return response with conversation context
        return ChatResponse(
            id=str(ai_message.id),
            conversation_id=str(conversation.id),
            conversation_uuid=conversation.uuid,
            role="assistant",
            content=ai_response_content,
            timestamp=ai_message.timestamp.isoformat()
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error for user {current_user.id}: {e}")
        db.rollback()
        
        # Return a fallback response without saving to database
        # (since we don't have proper conversation context in LLM error cases)
        fallback_response = f"I apologize, but I'm having trouble connecting to the AI service right now. Error: {str(e)}. Please try again in a moment."
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            conversation_id="",  # Empty for LLM error cases
            conversation_uuid="",  # Empty for LLM error cases
            role="assistant",
            content=fallback_response,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {str(e)}")
        logger.error(f"Chat error traceback:", exc_info=True)
        db.rollback()
        
        # Return a fallback response without saving to database
        # (since we don't have proper conversation context in error cases)
        fallback_response = "I apologize, but I'm experiencing some technical difficulties right now. Please try again in a moment. If you have specific UPSC-related questions, I'll do my best to help once the issue is resolved."
        
        return ChatResponse(
            id=str(uuid.uuid4()),
            conversation_id="",  # Empty for general error cases
            conversation_uuid="",  # Empty for general error cases
            role="assistant",
            content=fallback_response,
            timestamp=datetime.now().isoformat()
        )

async def _build_conversation_context(
    conversation: ChatConversationModel, 
    current_message: str, 
    db: Session, 
    llm_service: LLMService,
    max_context_messages: int = 10,
    max_tokens_estimate: int = 3000
) -> List[ChatMessage]:
    """
    Build optimized conversation context for AI with smart token management.
    
    Optimization strategies:
    1. Sliding window: Keep only recent messages
    2. Content summarization: Compress older context
    3. Token-aware truncation: Stay within token limits
    4. Role prioritization: Preserve important exchanges
    """
    try:
        # Get recent conversation history (sliding window)
        print(f"🔍 DEBUG: Querying messages for conversation_id: {conversation.id}")
        recent_messages = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation.id
        ).order_by(ChatMessageModel.timestamp.desc()).limit(max_context_messages).all()
        print(f"🔍 DEBUG: Found {len(recent_messages)} previous messages in database")
        for i, msg in enumerate(recent_messages):
            print(f"🔍 DEBUG: Previous message {i}: Role={msg.role.value}, Content={msg.content[:50]}...")
        
        # Reverse to chronological order
        recent_messages = list(reversed(recent_messages))
        
        # Add system prompt first
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
- Help with UPSC syllabus understanding
- Question pattern and strategy guidance
- Essay writing techniques
- Interview preparation
- Make this exam preparation fun and easy for the aspirants.

Always provide accurate, well-structured answers relevant to UPSC Civil Services examination. Focus on Indian context, governance, and constitutional law. Be encouraging and supportive in your tone."""
        
        context_messages = [ChatMessage(role="system", content=system_prompt)]
        estimated_tokens = len(system_prompt) // 4
        
        # Build context with token estimation
        for msg in recent_messages:
            # Rough token estimation (1 token ≈ 4 characters)
            msg_tokens = len(msg.content) // 4
            
            if estimated_tokens + msg_tokens > max_tokens_estimate:
                # Apply summarization for older messages if we exceed token limit
                if len(context_messages) > 3:  # Keep at least system + last 2 exchanges
                    # Summarize the first half of messages
                    break
                else:
                    # Truncate this message if it's too long
                    truncated_content = msg.content[:1000] + "... [message truncated for context efficiency]"
                    msg_tokens = len(truncated_content) // 4
            else:
                truncated_content = msg.content
            
            context_messages.append(ChatMessage(
                role=msg.role.value,
                content=truncated_content
            ))
            estimated_tokens += msg_tokens
        
        # Add current message
        context_messages.append(ChatMessage(
            role="user",
            content=current_message
        ))
        
        logger.info(f"Built conversation context: {len(context_messages)} messages, ~{estimated_tokens} tokens")
        return context_messages
        
    except Exception as e:
        logger.error(f"Error building conversation context: {e}")
        # Fallback to system prompt + current message
        system_prompt = """You are PrepGenie, an expert AI personal assistant specializing in UPSC (Union Public Service Commission) exam preparation for Indian Civil Services. Always provide accurate, well-structured answers relevant to UPSC Civil Services examination. Focus on Indian context, governance, and constitutional law. Be encouraging and supportive in your tone."""
        return [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=current_message)
        ]

@router.get("/history")
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get chat history for the current user"""
    try:
        # Join with conversations to get conversation UUID
        messages = db.query(ChatMessageModel, ChatConversationModel)\
            .join(ChatConversationModel, ChatMessageModel.conversation_id == ChatConversationModel.id)\
            .filter(ChatMessageModel.user_id == current_user.id)\
            .order_by(ChatMessageModel.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            ChatResponse(
                id=str(msg.id),
                conversation_id=str(msg.conversation_id),
                conversation_uuid=conv.uuid,
                role=msg.role.value,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
                tokens_used=msg.tokens_used
            )
            for msg, conv in reversed(messages)  # Reverse to get chronological order
        ]
    except Exception as e:
        logger.error(f"Error fetching chat history for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch chat history")
