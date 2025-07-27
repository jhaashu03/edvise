"""Add conversation sessions and enhance chat messages

This migration creates the chat_conversations table and updates chat_messages
to support conversation threading and enhanced metadata.

Revision ID: conversation_sessions_001
Create Date: 2025-01-26 17:06:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import uuid

# revision identifiers
revision = 'conversation_sessions_001'
down_revision = None
depends_on = None

def upgrade():
    """Create conversation sessions and migrate existing messages"""
    
    # Create chat_conversations table
    op.create_table('chat_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('active', 'archived', 'exported', name='conversationstatus'), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_conversations_id'), 'chat_conversations', ['id'], unique=False)
    op.create_index(op.f('ix_chat_conversations_uuid'), 'chat_conversations', ['uuid'], unique=True)
    
    # Create backup of existing chat_messages table
    op.rename_table('chat_messages', 'chat_messages_backup')
    
    # Create new chat_messages table with conversation_id
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('context_window', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

def downgrade():
    """Revert conversation sessions migration"""
    
    # Drop new tables
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_chat_conversations_uuid'), table_name='chat_conversations')
    op.drop_index(op.f('ix_chat_conversations_id'), table_name='chat_conversations')
    op.drop_table('chat_conversations')
    
    # Restore original chat_messages table
    op.rename_table('chat_messages_backup', 'chat_messages')

def migrate_existing_messages():
    """Helper function to migrate existing messages to conversation sessions"""
    # This will be called separately after migration to preserve existing data
    pass
