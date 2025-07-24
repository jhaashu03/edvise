#!/bin/bash

# PrepGenie Backend Setup Script
# This script helps set up the backend with PostgreSQL database

echo "🚀 PrepGenie Backend Setup"
echo "=========================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one from .env.example"
    exit 1
fi

# Check if DATABASE_URL is set to PostgreSQL
if grep -q "sqlite" .env; then
    echo "⚠️  Warning: DATABASE_URL appears to be using SQLite."
    echo "   Please update your .env file with your PostgreSQL connection string:"
    echo "   DATABASE_URL=postgresql://postgres:password@your-supabase-host:5432/postgres"
    echo ""
    echo "   Your Supabase connection string should look like:"
    echo "   postgresql://postgres.[project-ref]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
    echo ""
    read -p "   Have you updated the DATABASE_URL? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "   Please update DATABASE_URL in .env and run this script again."
        exit 1
    fi
fi

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🗃️  Setting up database migrations..."
# Initialize Alembic if not already done
if [ ! -d "alembic/versions" ]; then
    echo "   Creating alembic versions directory..."
    mkdir -p alembic/versions
fi

# Create initial migration
echo "   Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

# Run migrations
echo "   Running database migrations..."
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Update your .env file with the correct PostgreSQL connection string"
echo "   2. Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo "   3. Test the API at: http://localhost:8000/docs"
echo ""
echo "🔗 Your API endpoints will be available at:"
echo "   - Health check: http://localhost:8000/api/v1/health"
echo "   - Registration: http://localhost:8000/api/v1/auth/register"
echo "   - API docs: http://localhost:8000/docs"
