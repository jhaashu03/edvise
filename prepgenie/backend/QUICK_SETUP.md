# PrepGenie Backend Setup Guide

## Quick Setup for PostgreSQL Database

### 1. Database Configuration

Update your `.env` file with your Supabase PostgreSQL connection string:

```bash
# Replace with your actual Supabase connection string
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database (automated)
python setup_db.py

# OR manual setup
alembic upgrade head
```

### 3. Start the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the Setup

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Registration: http://localhost:8000/api/v1/auth/register

## Troubleshooting

### "Not Found" Error on Registration

This usually means:
1. Database connection failed - check your DATABASE_URL
2. Tables haven't been created - run `python setup_db.py`
3. Wrong API endpoint - ensure you're using `/api/v1/auth/register`

### Database Connection Issues

1. **Check Supabase credentials**: Ensure your connection string is correct
2. **Network access**: Verify your IP is allowed in Supabase settings
3. **SSL requirements**: Supabase requires SSL connections (handled automatically)

### Common Connection String Formats

**Supabase:**
```
postgresql://postgres.[project-ref]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

**Local PostgreSQL:**
```
postgresql://username:password@localhost:5432/prepgenie
```

## Environment Variables

Copy `.env.example` to `.env` and update:

- `DATABASE_URL`: Your PostgreSQL connection string
- `SECRET_KEY`: Random string for JWT signing
- `MILVUS_URI`: Your Zilliz cloud instance URL
- `MILVUS_TOKEN`: Your Zilliz authentication token
- `OPENAI_API_KEY`: OpenAI API key (optional)

## API Endpoints

The backend provides the following main endpoints:

- **Authentication**: `/api/v1/auth/*`
- **Study Plans**: `/api/v1/study-plans/*`
- **Answer Evaluation**: `/api/v1/answers/*`
- **Chat**: `/api/v1/chat/*`
- **PYQ**: `/api/v1/pyq/*`
- **Progress**: `/api/v1/progress/*`

All endpoints are documented at `/docs` when the server is running.
