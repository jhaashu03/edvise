#!/usr/bin/env python3
"""
Initialize complete chat database schema.
Creates all necessary tables for the chat system including conversation management.
"""

import sqlite3
import os
from datetime import datetime

def init_chat_schema():
    """Initialize complete chat database schema"""
    
    db_path = "prepgenie.db"
    print(f"🔄 Initializing chat schema in: {db_path}")
    
    # Create backup if database exists
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"📦 Database backup created: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create users table if it doesn't exist (chat system depends on it)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                hashed_password TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ users table ready")
        
        # Create chat_conversations table (enhanced version)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                topic TEXT,
                summary TEXT,
                status TEXT DEFAULT 'active',
                message_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_pinned BOOLEAN DEFAULT 0,
                tags TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        print("✅ chat_conversations table ready")
        
        # Create chat_messages table (the missing fundamental table!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER,
                context_window TEXT,
                FOREIGN KEY (conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        print("✅ chat_messages table created (CRITICAL MISSING TABLE)")
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_id 
            ON chat_conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_conversations_uuid 
            ON chat_conversations(uuid)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_conversations_status 
            ON chat_conversations(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id 
            ON chat_messages(conversation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id 
            ON chat_messages(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp 
            ON chat_messages(timestamp)
        """)
        print("✅ Database indexes created")
        
        # Create a test user if no users exist (for development)
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            cursor.execute("""
                INSERT INTO users (username, email, full_name, hashed_password)
                VALUES (?, ?, ?, ?)
            """, ("testuser", "test@example.com", "Test User", "hashed_password_here"))
            print("✅ Test user created (id: 1)")
        
        conn.commit()
        print("🎉 Chat database schema initialization completed successfully!")
        
        # Show schema summary
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"\n📊 Database Summary:")
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            print(f"   - {table_name}: {row_count} rows")
        
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_chat_schema()
