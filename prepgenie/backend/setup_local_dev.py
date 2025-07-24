#!/usr/bin/env python3
"""
Local Development Setup - Use SQLite instead of Supabase for local development
This allows you to develop locally while your production uses Supabase
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_local_env():
    """Create a local development .env file using SQLite"""
    
    env_path = Path(".env.local")
    
    content = """# Local Development Environment
# Use SQLite for local development to avoid network issues
DATABASE_URL=sqlite:///./prepgenie_local.db

# Keep other settings
SECRET_KEY=your-local-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# OpenAI (use your real key)
OPENAI_API_KEY=your-openai-key-here
OPENAI_MODEL=gpt-4
LLM_PROVIDER=openai

# Alternative: Walmart LLM Gateway (uncomment to use)
# LLM_PROVIDER=walmart_gateway
# WALMART_LLM_GATEWAY_API_KEY=your-walmart-api-key
# WALMART_LLM_GATEWAY_BASE_URL=https://wmtllmgateway.stage.walmart.com/wmtllmgateway
# WALMART_LLM_GATEWAY_MODEL=gpt-4.1-mini
# WALMART_LLM_GATEWAY_SVC_ENV=stage

# Milvus (keep production settings or use local)
MILVUS_URI=https://in03-7399fcefb79acf1.serverless.gcp-us-west1.cloud.zilliz.com
MILVUS_TOKEN=your-milvus-token-here

# Local development flags
ENVIRONMENT=local
DEBUG=true
"""
    
    try:
        with open(env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Created {env_path} for local development")
        print("📝 Remember to update OPENAI_API_KEY and MILVUS_TOKEN")
        return True
        
    except Exception as e:
        print(f"❌ Error creating {env_path}: {e}")
        return False

def update_config_for_sqlite():
    """Update config.py to support SQLite for local development"""
    
    config_path = Path("app/core/config.py")
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Add environment detection
        if 'ENVIRONMENT' not in content:
            addition = '''
    # Environment detection
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    @property
    def DATABASE_URL(self) -> str:
        # Use SQLite for local development
        if self.ENVIRONMENT == "local":
            return "sqlite:///./prepgenie_local.db"
        
        # Use Supabase for production
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?sslmode=require&gssencmode=disable"
'''
            
            # Replace the DATABASE_URL property
            old_property = '''    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        # URL encode the password to handle special characters
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?sslmode=require&gssencmode=disable"'''
            
            if old_property in content:
                content = content.replace(old_property, addition.strip())
                
                with open(config_path, 'w') as f:
                    f.write(content)
                
                print("✅ Updated config.py to support SQLite for local development")
                return True
        
        print("⚠️  Could not update config.py automatically")
        return False
        
    except Exception as e:
        print(f"❌ Error updating config.py: {e}")
        return False

def install_sqlite_deps():
    """Install SQLite dependencies for local development"""
    
    print("📦 Installing SQLite dependencies...")
    
    try:
        import subprocess
        
        subprocess.run([sys.executable, "-m", "pip", "install", "aiosqlite"], check=True)
        print("✅ Installed aiosqlite for SQLite support")
        
        # Update requirements.txt
        with open("requirements.txt", "a") as f:
            f.write("\naiosqlite==0.20.0\n")
        
        print("✅ Added aiosqlite to requirements.txt")
        return True
        
    except Exception as e:
        print(f"❌ Error installing SQLite dependencies: {e}")
        return False

def test_local_setup():
    """Test the local SQLite setup"""
    
    print("\n🧪 Testing Local SQLite Setup")
    print("=" * 40)
    
    # Set environment for testing
    os.environ["ENVIRONMENT"] = "local"
    
    try:
        sys.path.append(str(Path(__file__).resolve().parent))
        from app.core.config import settings
        from app.db.database import Base, engine
        from sqlalchemy import text
        
        print(f"📋 Database URL: {settings.DATABASE_URL}")
        print(f"🌍 Environment: {settings.ENVIRONMENT}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Created SQLite tables")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT sqlite_version();"))
            version = result.fetchone()[0]
            print(f"📊 SQLite version: {version}")
            
            # Test table creation
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📁 Created {len(tables)} tables: {', '.join(tables)}")
        
        engine.dispose()
        print("✅ Local SQLite setup is working!")
        return True
        
    except Exception as e:
        print(f"❌ Local setup test failed: {e}")
        return False

def create_local_start_script():
    """Create a script to start the server in local mode"""
    
    script_content = '''#!/usr/bin/env python3
"""Start PrepGenie in local development mode with SQLite"""

import os
import subprocess
import sys

# Set environment to local
os.environ["ENVIRONMENT"] = "local"

# Load local environment
from dotenv import load_dotenv
load_dotenv(".env.local")

print("🚀 Starting PrepGenie in LOCAL DEVELOPMENT mode")
print("📁 Using SQLite database: ./prepgenie_local.db")
print("🌐 Server will be available at: http://localhost:8000")
print("📚 API docs: http://localhost:8000/docs")
print()

# Start the server
try:
    subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"], check=True)
except KeyboardInterrupt:
    print("\\n👋 Server stopped")
except Exception as e:
    print(f"❌ Error starting server: {e}")
'''
    
    with open("start_local.py", "w") as f:
        f.write(script_content)
    
    # Make executable
    os.chmod("start_local.py", 0o755)
    
    print("✅ Created start_local.py script")
    return True

def main():
    print("🏠 PrepGenie Local Development Setup")
    print("=" * 40)
    print("This will set up SQLite for local development")
    print("to avoid network connectivity issues with Supabase.")
    print()
    
    steps = [
        ("Installing SQLite dependencies", install_sqlite_deps),
        ("Creating local environment file", create_local_env), 
        ("Updating configuration", update_config_for_sqlite),
        ("Creating start script", create_local_start_script),
        ("Testing setup", test_local_setup),
    ]
    
    for step_name, step_func in steps:
        print(f"🔄 {step_name}...")
        if not step_func():
            print(f"❌ Failed: {step_name}")
            return False
        print()
    
    print("🎉 Local development setup complete!")
    print()
    print("📋 Next Steps:")
    print("1. Update .env.local with your OpenAI API key")
    print("2. Run: python start_local.py")
    print("3. Test: http://localhost:8000/docs")
    print("4. For production: Deploy to Railway/Vercel with Supabase")
    print()
    print("💡 Benefits:")
    print("✅ No network connectivity issues")
    print("✅ Fast local development")  
    print("✅ Offline development possible")
    print("✅ Production still uses Supabase")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
