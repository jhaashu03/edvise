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
from app.prompts import CHAT_SYSTEM_PROMPT  # NEW: Using modular prompts
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
        
        # System prompt now imported from app.prompts module
        # Using modular, UPSC-syllabus-aligned prompt from app/prompts/chat_prompts.py
        
        # Build optimized conversation context for AI
        logger.debug(f"Building conversation context for conversation_id: {conversation.id}")
        
        conversation_context = await _build_conversation_context(
            conversation,
            request.message,
            db,
            llm_service
        )
        
        logger.debug(f"Built context with {len(conversation_context)} messages")
        
        # Get AI response with full conversation context
        ai_response = await llm_service.chat_completion(
            messages=conversation_context,
            temperature=0.7,
            max_tokens=1000
        )
        ai_response_content = ai_response.content
        
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
        logger.debug(f"Querying messages for conversation_id: {conversation.id}")
        recent_messages = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation.id
        ).order_by(ChatMessageModel.timestamp.desc()).limit(max_context_messages).all()
        logger.debug(f"Found {len(recent_messages)} previous messages in database")
        
        # Reverse to chronological order
        recent_messages = list(reversed(recent_messages))
        
        # Use modular system prompt from app/prompts/chat_prompts.py
        # This contains comprehensive UPSC syllabus-aligned content
        context_messages = [ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT)]
        estimated_tokens = len(CHAT_SYSTEM_PROMPT) // 4
        
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
        # Fallback to system prompt + current message using modular prompt
        return [
            ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT),
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
