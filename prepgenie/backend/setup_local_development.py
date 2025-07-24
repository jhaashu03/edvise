#!/usr/bin/env python3
"""
Setup script for local development with SQLite.
This script will configure the environment for local development and test the FastAPI app.
"""
import os
import subprocess
import sys
from pathlib import Path

def setup_local_environment():
    """Setup local environment variables"""
    print("🔧 Setting up local development environment...")
    
    # Read current .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Check if ENVIRONMENT=local is already set
    if "ENVIRONMENT=local" in content:
        print("✅ ENVIRONMENT=local already set in .env")
    else:
        # Add ENVIRONMENT=local to the .env file
        with open(env_file, 'a') as f:
            f.write("\n# Local Development\nENVIRONMENT=local\n")
        print("✅ Added ENVIRONMENT=local to .env file")
    
    return True

def test_fastapi_startup():
    """Test if FastAPI can start up properly"""
    print("\n🚀 Testing FastAPI startup...")
    
    try:
        # Import FastAPI app to test startup
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        # Test database connection
        from app.db.database import test_db_connection
        if test_db_connection():
            print("✅ Database connection test passed")
        else:
            print("❌ Database connection test failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ FastAPI startup test failed: {e}")
        return False

def run_basic_server_test():
    """Run a basic server test to ensure everything works"""
    print("\n🌐 Testing server startup...")
    
    try:
        # Try to start the server in test mode
        import uvicorn
        from app.main import app
        
        print("✅ Server components loaded successfully")
        print("💡 You can now start the server with:")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
        return True
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False

def create_test_user():
    """Create a test user in the database"""
    print("\n👤 Testing user creation...")
    
    try:
        from app.db.database import SessionLocal
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError
        
        db = SessionLocal()
        
        # Check if test user already exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            print("✅ Test user already exists")
            db.close()
            return True
        
        # Create test user
        test_user = User(
            email="test@example.com",
            hashed_password="$2b$12$test.hash.for.testing.only",  # This is just for testing
            full_name="Test User"
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        db.close()
        
        print(f"✅ Created test user: {test_user.email} (ID: {test_user.id})")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test user: {e}")
        return False

def main():
    """Main setup function"""
    print("🏗️  PrepGenie Local Development Setup")
    print("=" * 50)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Step 1: Setup local environment
    if not setup_local_environment():
        print("❌ Failed to setup environment")
        return
    
    # Step 2: Test database connection
    print("\n📋 Running database test...")
    result = subprocess.run([sys.executable, "test_prepgenie_db.py"], 
                          capture_output=True, text=True)
    if "Local SQLite setup working correctly" in result.stdout:
        print("✅ Database test passed")
    else:
        print("❌ Database test failed")
        print(result.stdout)
        return
    
    # Step 3: Test FastAPI startup
    if not test_fastapi_startup():
        print("❌ FastAPI startup test failed")
        return
    
    # Step 4: Test server components
    if not run_basic_server_test():
        print("❌ Server component test failed")
        return
    
    # Step 5: Create test user
    create_test_user()
    
    print("\n🎉 Local development setup complete!")
    print("=" * 50)
    print("📋 Next steps:")
    print("1. Start the server:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("")
    print("2. Test the API:")
    print("   http://localhost:8000/docs")
    print("")
    print("3. Database info:")
    print("   - Using SQLite: prepgenie_local.db")
    print("   - Test user: test@example.com")
    print("")
    print("4. When ready for production:")
    print("   - Remove ENVIRONMENT=local from .env")
    print("   - Fix Supabase IP allowlist issue")
    print("   - Add IP 103.158.254.109 to Supabase allowlist")

if __name__ == "__main__":
    main()
