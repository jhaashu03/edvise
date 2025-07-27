"""
Enhanced conversation management API endpoints for chat sessions.

Provides comprehensive conversation session management including:
- List conversations with pagination and filtering
- Search conversations by content and metadata
- Update conversation metadata (title, tags, status)
- Archive and export conversations
- Conversation statistics and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.user import User
from app.models.chat import (
    ChatConversation as ChatConversationModel,
    ChatMessage as ChatMessageModel,
    ConversationStatus,
    MessageRole
)
from app.api.api_v1.endpoints.auth import get_current_user
from app.core.llm_service import get_llm_service, LLMService
from app.utils.conversation_manager import ConversationManager
import logging
import json
from sqlalchemy import desc, asc, func

logger = logging.getLogger(__name__)
router = APIRouter()

# Response Models
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
    first_message_preview: Optional[str] = None
    last_message_time: Optional[str] = None

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    per_page: int
    has_next: bool

class ConversationStatsResponse(BaseModel):
    active_conversations: int
    archived_conversations: int
    total_messages: int
    conversations_this_week: int
    most_active_topics: List[Dict[str, Any]]

class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = None
    status: Optional[str] = None

class ConversationSearchRequest(BaseModel):
    query: str
    status: Optional[str] = "active"
    topic: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query("active"),
    topic: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("updated_at", regex="^(created_at|updated_at|title|message_count)$"),
    sort_order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List conversations with pagination, filtering, and sorting"""
    try:
        # Build query
        query = db.query(ChatConversationModel).filter(
            ChatConversationModel.user_id == current_user.id
        )
        
        # Apply status filter
        if status and status != "all":
            try:
                status_enum = ConversationStatus(status)
                query = query.filter(ChatConversationModel.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Apply topic filter
        if topic:
            query = query.filter(ChatConversationModel.topic.ilike(f"%{topic}%"))
        
        # Apply sorting
        sort_column = getattr(ChatConversationModel, sort_by, ChatConversationModel.updated_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        conversations = query.offset(offset).limit(per_page).all()
        
        # Build response with additional metadata
        conversation_responses = []
        for conv in conversations:
            # Get first and last message previews
            first_message = db.query(ChatMessageModel).filter(
                ChatMessageModel.conversation_id == conv.id,
                ChatMessageModel.role == MessageRole.user
            ).order_by(ChatMessageModel.timestamp.asc()).first()
            
            last_message = db.query(ChatMessageModel).filter(
                ChatMessageModel.conversation_id == conv.id
            ).order_by(ChatMessageModel.timestamp.desc()).first()
            
            conversation_responses.append(ConversationResponse(
                id=str(conv.id),
                uuid=conv.uuid,
                title=conv.title,
                topic=conv.topic,
                summary=conv.summary,
                status=conv.status.value,
                message_count=conv.message_count,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                is_pinned=conv.is_pinned,
                tags=conv.tags,
                first_message_preview=first_message.content[:100] + "..." if first_message and len(first_message.content) > 100 else first_message.content if first_message else None,
                last_message_time=last_message.timestamp.isoformat() if last_message else None
            ))
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=total > page * per_page
        )
        
    except Exception as e:
        logger.error(f"Error listing conversations for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not list conversations")

@router.post("/conversations/search", response_model=ConversationListResponse)
async def search_conversations(
    request: ConversationSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Search conversations by content, title, topic, and metadata"""
    try:
        conversation_manager = ConversationManager(llm_service)
        conversations = conversation_manager.search_conversations(
            user_id=current_user.id,
            query=request.query,
            db=db
        )
        
        # Apply additional filters
        if request.topic:
            conversations = [c for c in conversations if c.topic and request.topic.lower() in c.topic.lower()]
        
        if request.date_from:
            date_from = datetime.fromisoformat(request.date_from.replace('Z', '+00:00'))
            conversations = [c for c in conversations if c.created_at >= date_from]
        
        if request.date_to:
            date_to = datetime.fromisoformat(request.date_to.replace('Z', '+00:00'))
            conversations = [c for c in conversations if c.created_at <= date_to]
        
        # Build response
        conversation_responses = []
        for conv in conversations:
            conversation_responses.append(ConversationResponse(
                id=str(conv.id),
                uuid=conv.uuid,
                title=conv.title,
                topic=conv.topic,
                summary=conv.summary,
                status=conv.status.value,
                message_count=conv.message_count,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                is_pinned=conv.is_pinned,
                tags=conv.tags
            ))
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=len(conversation_responses),
            page=1,
            per_page=len(conversation_responses),
            has_next=False
        )
        
    except Exception as e:
        logger.error(f"Error searching conversations for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not search conversations")

@router.get("/conversations/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Get conversation statistics and analytics"""
    try:
        conversation_manager = ConversationManager(llm_service)
        stats = conversation_manager.get_conversation_stats(current_user.id, db)
        
        # Get conversations from this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        conversations_this_week = db.query(ChatConversationModel).filter(
            ChatConversationModel.user_id == current_user.id,
            ChatConversationModel.created_at >= week_ago
        ).count()
        
        # Get most active topics
        topic_stats = db.query(
            ChatConversationModel.topic,
            func.count(ChatConversationModel.id).label('count')
        ).filter(
            ChatConversationModel.user_id == current_user.id,
            ChatConversationModel.topic.isnot(None)
        ).group_by(ChatConversationModel.topic).order_by(desc('count')).limit(5).all()
        
        most_active_topics = [
            {"topic": topic, "count": count} for topic, count in topic_stats
        ]
        
        return ConversationStatsResponse(
            active_conversations=stats["active_conversations"],
            archived_conversations=stats["archived_conversations"],
            total_messages=stats["total_messages"],
            conversations_this_week=conversations_this_week,
            most_active_topics=most_active_topics
        )
        
    except Exception as e:
        logger.error(f"Error getting stats for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not get conversation stats")

@router.put("/conversations/{conversation_uuid}", response_model=ConversationResponse)
async def update_conversation(
    conversation_uuid: str,
    request: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation metadata"""
    try:
        # Find conversation
        conversation = db.query(ChatConversationModel).filter(
            ChatConversationModel.uuid == conversation_uuid,
            ChatConversationModel.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update fields
        if request.title is not None:
            conversation.title = request.title
        
        if request.tags is not None:
            conversation.tags = request.tags
        
        if request.is_pinned is not None:
            conversation.is_pinned = request.is_pinned
        
        if request.status is not None:
            try:
                conversation.status = ConversationStatus(request.status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        return ConversationResponse(
            id=str(conversation.id),
            uuid=conversation.uuid,
            title=conversation.title,
            topic=conversation.topic,
            summary=conversation.summary,
            status=conversation.status.value,
            message_count=conversation.message_count,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            is_pinned=conversation.is_pinned,
            tags=conversation.tags
        )
        
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Could not update conversation")

@router.delete("/conversations/{conversation_uuid}")
async def delete_conversation(
    conversation_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        # Find conversation
        conversation = db.query(ChatConversationModel).filter(
            ChatConversationModel.uuid == conversation_uuid,
            ChatConversationModel.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete conversation (messages will be deleted due to cascade)
        db.delete(conversation)
        db.commit()
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Could not delete conversation")

@router.post("/conversations/{conversation_uuid}/archive")
async def archive_conversation(
    conversation_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a conversation"""
    try:
        # Find conversation
        conversation = db.query(ChatConversationModel).filter(
            ChatConversationModel.uuid == conversation_uuid,
            ChatConversationModel.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation.status = ConversationStatus.archived
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Conversation archived successfully"}
        
    except Exception as e:
        logger.error(f"Error archiving conversation {conversation_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Could not archive conversation")

@router.post("/conversations/{conversation_uuid}/export")
async def export_conversation(
    conversation_uuid: str,
    format: str = Query("json", regex="^(json|txt|md)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export conversation in various formats"""
    try:
        # Find conversation with messages
        conversation = db.query(ChatConversationModel).filter(
            ChatConversationModel.uuid == conversation_uuid,
            ChatConversationModel.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get all messages
        messages = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation.id
        ).order_by(ChatMessageModel.timestamp.asc()).all()
        
        if format == "json":
            export_data = {
                "conversation": {
                    "title": conversation.title,
                    "topic": conversation.topic,
                    "summary": conversation.summary,
                    "created_at": conversation.created_at.isoformat(),
                    "message_count": conversation.message_count
                },
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    } for msg in messages
                ]
            }
            return export_data
        
        elif format == "txt":
            export_text = f"Conversation: {conversation.title}\n"
            export_text += f"Topic: {conversation.topic or 'General'}\n"
            export_text += f"Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            export_text += "=" * 50 + "\n\n"
            
            for msg in messages:
                role = "You" if msg.role == MessageRole.user else "PrepGenie"
                export_text += f"{role} ({msg.timestamp.strftime('%H:%M')}):\n{msg.content}\n\n"
            
            return {"content": export_text, "filename": f"{conversation.title.replace(' ', '_')}.txt"}
        
        elif format == "md":
            export_md = f"# {conversation.title}\n\n"
            export_md += f"**Topic:** {conversation.topic or 'General'}  \n"
            export_md += f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M')}  \n"
            export_md += f"**Messages:** {conversation.message_count}\n\n"
            
            if conversation.summary:
                export_md += f"**Summary:** {conversation.summary}\n\n"
            
            export_md += "---\n\n"
            
            for msg in messages:
                role = "**You**" if msg.role == MessageRole.user else "**PrepGenie**"
                timestamp = msg.timestamp.strftime('%H:%M')
                export_md += f"{role} _{timestamp}_:\n\n{msg.content}\n\n"
            
            return {"content": export_md, "filename": f"{conversation.title.replace(' ', '_')}.md"}
        
    except Exception as e:
        logger.error(f"Error exporting conversation {conversation_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Could not export conversation")
