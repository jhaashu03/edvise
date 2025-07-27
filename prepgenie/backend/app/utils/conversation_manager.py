"""
Conversation management utilities for chat session handling.

This module provides utilities for:
- Auto-generating conversation titles and topics
- Managing conversation sessions
- Topic detection and categorization
- Conversation summarization
"""

import re
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from app.models.chat import ChatConversation, ChatMessage, ConversationStatus
from app.core.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation sessions, titles, topics, and metadata"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        
    # UPSC topic categories for auto-detection
    UPSC_TOPICS = {
        'polity': ['constitution', 'polity', 'parliament', 'judiciary', 'governance', 'federal', 'rights', 'directive principles'],
        'history': ['ancient', 'medieval', 'modern', 'freedom struggle', 'independence', 'mughal', 'british'],
        'geography': ['physical', 'human', 'economic geography', 'climate', 'monsoon', 'rivers', 'mountains'],
        'economics': ['economy', 'gdp', 'inflation', 'budget', 'fiscal', 'monetary', 'trade', 'agriculture'],
        'current_affairs': ['current', 'recent', 'news', 'government scheme', 'policy', 'international'],
        'environment': ['environment', 'ecology', 'biodiversity', 'climate change', 'pollution', 'forest'],
        'science_tech': ['science', 'technology', 'space', 'biotechnology', 'nuclear', 'research'],
        'ethics': ['ethics', 'integrity', 'moral', 'values', 'case study', 'dilemma']
    }

    async def create_conversation(self, user_id: int, first_message: str, db: Session) -> ChatConversation:
        """Create a new conversation with auto-generated title and topic"""
        
        # Generate title and detect topic
        title = await self._generate_title(first_message)
        topic = self._detect_topic(first_message)
        
        # Create conversation
        conversation = ChatConversation(
            user_id=user_id,
            title=title,
            topic=topic,
            message_count=0,
            status=ConversationStatus.active
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"Created conversation {conversation.uuid} with title: {title}, topic: {topic}")
        return conversation

    async def _generate_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message"""
        try:
            # Use first 100 chars for title generation
            prompt_text = first_message[:100] + "..." if len(first_message) > 100 else first_message
            
            system_prompt = """Generate a concise, descriptive title (max 50 characters) for a UPSC preparation chat conversation based on the first message. 

Rules:
- Keep it under 50 characters
- Focus on the main topic/question
- Use UPSC-relevant terminology
- Make it searchable and clear
- Don't include "UPSC" in every title

Examples:
"Constitutional Amendment Process" 
"Monsoon Pattern Analysis"
"Economic Survey 2024 Highlights"
"Ethics Case Study Discussion"
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate title for: {prompt_text}"}
            ]
            
            response = await self.llm_service.simple_chat(
                user_message=first_message[:500],  # Use first part of message
                system_prompt="Generate a concise, descriptive title (max 8 words) for a UPSC exam preparation conversation based on this message. Focus on the main topic or subject area.",
                max_tokens=60
            )
            title = response.strip().replace('"', '').replace("'", "")
            
            # Fallback if title is too long or empty
            if len(title) > 50 or len(title) < 5:
                title = self._extract_title_keywords(first_message)
                
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return self._extract_title_keywords(first_message)

    def _extract_title_keywords(self, text: str) -> str:
        """Extract keywords for title as fallback"""
        # Remove common words and extract key terms
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Common UPSC terms that make good titles
        key_terms = []
        for word in words:
            if len(word) > 3 and word not in ['what', 'how', 'why', 'when', 'where', 'the', 'and', 'for', 'with']:
                key_terms.append(word.title())
                if len(key_terms) >= 3:
                    break
        
        if key_terms:
            return " ".join(key_terms)[:50]
        else:
            return "UPSC Discussion"

    def _detect_topic(self, text: str) -> Optional[str]:
        """Detect UPSC topic category from message content"""
        text_lower = text.lower()
        
        # Count matches for each topic
        topic_scores = {}
        for topic, keywords in self.UPSC_TOPICS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                topic_scores[topic] = score
        
        # Return topic with highest score
        if topic_scores:
            return max(topic_scores, key=topic_scores.get).replace('_', ' ').title()
        
        return None

    async def update_conversation_metadata(self, conversation: ChatConversation, db: Session):
        """Update conversation metadata after new messages"""
        # Update message count
        message_count = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation.id
        ).count()
        
        conversation.message_count = message_count
        conversation.updated_at = datetime.utcnow()
        
        # Generate summary if conversation has enough messages
        if message_count >= 5 and not conversation.summary:
            conversation.summary = await self._generate_summary(conversation, db)
        
        db.commit()

    async def _generate_summary(self, conversation: ChatConversation, db: Session) -> str:
        """Generate conversation summary"""
        try:
            # Get recent messages for summary
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
            
            if not messages:
                return ""
            
            # Calculate message count for summary
            message_count = len(messages)
            
            # Prepare conversation context
            conversation_text = "\n".join([
                f"{msg.role.value}: {msg.content[:200]}..." if len(msg.content) > 200 else f"{msg.role.value}: {msg.content}"
                for msg in reversed(messages)
            ])
            
            summary_prompt = f"""Create a concise summary (max 150 characters) of this UPSC preparation conversation:

{conversation_text}

Focus on:
- Main topics discussed
- Key concepts covered
- Questions asked
- Learning outcomes

Summary:"""
            
            messages_for_llm = [
                {"role": "system", "content": "You are a UPSC preparation assistant. Create concise conversation summaries."},
                {"role": "user", "content": summary_prompt}
            ]
            
            response = await self.llm_service.simple_chat(
                user_message=f"Summarize this UPSC conversation with {message_count} messages. Focus on key topics, questions asked, and concepts discussed. Keep it concise (max 100 words).",
                system_prompt="You are a UPSC preparation assistant. Create clear, informative conversation summaries.",
                max_tokens=150
            )
            return response.strip()[:150]
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Discussion about {conversation.topic or 'UPSC topics'}"

    def search_conversations(self, user_id: int, query: str, db: Session) -> List[ChatConversation]:
        """Search conversations by title, topic, tags, or content"""
        search_terms = query.lower().split()
        
        conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == user_id,
            ChatConversation.status == ConversationStatus.active
        )
        
        # Search in title, topic, tags, and summary
        for term in search_terms:
            conversations = conversations.filter(
                ChatConversation.title.ilike(f"%{term}%") |
                ChatConversation.topic.ilike(f"%{term}%") |
                ChatConversation.tags.ilike(f"%{term}%") |
                ChatConversation.summary.ilike(f"%{term}%")
            )
        
        return conversations.order_by(ChatConversation.updated_at.desc()).all()

    def get_conversation_stats(self, user_id: int, db: Session) -> Dict:
        """Get conversation statistics for user"""
        active_count = db.query(ChatConversation).filter(
            ChatConversation.user_id == user_id,
            ChatConversation.status == ConversationStatus.active
        ).count()
        
        archived_count = db.query(ChatConversation).filter(
            ChatConversation.user_id == user_id,
            ChatConversation.status == ConversationStatus.archived
        ).count()
        
        total_messages = db.query(ChatMessage).join(ChatConversation).filter(
            ChatConversation.user_id == user_id
        ).count()
        
        return {
            "active_conversations": active_count,
            "archived_conversations": archived_count,
            "total_messages": total_messages
        }
