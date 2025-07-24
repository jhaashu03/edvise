#!/usr/bin/env python3
"""
PrepGenie Database Setup Script
Helps verify database connection and initialize the database schema.
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.db.database import Base
from app.models import *  # Import all models

def test_database_connection():
    """Test the database connection."""
    print("🔍 Testing database connection...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nPossible issues:")
        print("1. Check your DATABASE_URL in .env file")
        print("2. Ensure your Supabase database is accessible")
        print("3. Verify your credentials are correct")
        return False

def create_tables():
    """Create database tables."""
    print("🗃️  Creating database tables...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def main():
    print("🚀 PrepGenie Database Setup")
    print("===========================")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("Please create a .env file with your database configuration.")
        return False
    
    # Display current database URL (masked for security)
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        # Mask password in URL for display
        masked_url = db_url.split("://")[0] + "://***:***@" + db_url.split("@")[1]
        print(f"🔗 Database URL: {masked_url}")
    else:
        print(f"⚠️  Database URL: {db_url}")
        print("Warning: This doesn't appear to be a PostgreSQL URL")
    
    # Test connection
    if not test_database_connection():
        return False
    
    # Create tables
    if not create_tables():
        return False
    
    print("\n✅ Database setup complete!")
    print("\n📋 Next steps:")
    print("1. Start the server: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    print("2. Test registration: http://localhost:8000/docs")
    print("3. Check health endpoint: http://localhost:8000/api/v1/health")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
