#!/usr/bin/env python3
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
    print("\n👋 Server stopped")
except Exception as e:
    print(f"❌ Error starting server: {e}")
