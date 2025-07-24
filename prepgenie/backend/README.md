# PrepGenie Backend

FastAPI backend for PrepGenie - Your Personalized UPSC AI Mentor.

## Features

- 🔐 **JWT Authentication** - Secure user authentication and authorization
- 📚 **RESTful API** - Clean, well-documented API endpoints
- 🗄️ **PostgreSQL Database** - Robust data storage with SQLAlchemy ORM
- 🔍 **Vector Search** - Milvus integration for semantic PYQ search
- 🤖 **AI Integration** - OpenAI GPT-4 for answer evaluation and chat
- 📄 **PDF Processing** - Extract and process answer uploads
- 🚀 **High Performance** - Async FastAPI with optimized database queries

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── api_v1/
│   │       └── endpoints/     # API route handlers
│   ├── core/                  # Core utilities (config, security)
│   ├── crud/                  # Database operations
│   ├── db/                    # Database configuration
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   └── services/              # Business logic services
├── alembic/                   # Database migrations
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── main.py                   # FastAPI application entry point
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL database
- OpenAI API key
- Milvus instance (Zilliz Cloud recommended)

### 2. Installation

```bash
# Clone the repository
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Update the following variables in `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost/prepgenie
SECRET_KEY=your-super-secret-jwt-key
OPENAI_API_KEY=your-openai-api-key
MILVUS_URI=https://your-milvus-instance.zillizcloud.com
MILVUS_TOKEN=your-milvus-token
```

### 4. Database Setup

```bash
# Initialize database migrations
alembic upgrade head

# Or create initial migration if needed
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 5. Run the Application

```bash
# Development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:

- **API Docs (Swagger)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/v1/openapi.json`

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user

### Study Plans
- `GET /api/v1/study-plans/me` - Get user's study plan
- `POST /api/v1/study-plans` - Create study plan
- `PATCH /api/v1/study-plans/targets/{id}` - Update study target

### PYQ Search
- `POST /api/v1/pyqs/search` - Semantic search for PYQs
- `GET /api/v1/pyqs/subject/{subject}` - Get PYQs by subject

### Answer Evaluation
- `POST /api/v1/answers/upload` - Upload answer for evaluation
- `GET /api/v1/answers/me` - Get user's answers
- `GET /api/v1/answers/{id}/evaluation` - Get answer evaluation

### Chat & AI
- `POST /api/v1/chat` - Send chat message to AI

### Progress Analytics
- `GET /api/v1/progress/me` - Get user progress data

### Syllabus
- `GET /api/v1/syllabus` - Get UPSC syllabus
- `GET /api/v1/syllabus/{subject}` - Get subject syllabus

## Database Models

### Core Models
- **User**: User accounts and authentication
- **StudyPlan**: Personalized study schedules
- **StudyTarget**: Individual study goals
- **PYQ**: Past Year Questions with metadata
- **UploadedAnswer**: User answer submissions
- **AnswerEvaluation**: AI evaluation results
- **ChatMessage**: Chat conversation history
- **SyllabusItem**: UPSC syllabus structure

## AI Services

### Vector Search (Milvus)
- Semantic search for PYQs using embeddings
- Topic-based question retrieval
- Content similarity matching

### OpenAI Integration
- Answer evaluation using GPT-4
- Feedback generation
- Chat assistance
- Study recommendations

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

## Deployment

### Railway Deployment

1. **Prepare for deployment**:
   ```bash
   # Ensure requirements.txt is updated
   pip freeze > requirements.txt
   ```

2. **Railway setup**:
   - Connect GitHub repository to Railway
   - Set environment variables in Railway dashboard
   - Deploy automatically on push to main branch

3. **Environment variables for production**:
   ```env
   DATABASE_URL=postgresql://...  # Railway PostgreSQL
   SECRET_KEY=production-secret-key
   OPENAI_API_KEY=your-key
   MILVUS_URI=your-production-milvus
   BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Development

### Adding New Endpoints

1. **Create schema** in `app/schemas/`
2. **Create model** in `app/models/`
3. **Add CRUD operations** in `app/crud/`
4. **Create endpoint** in `app/api/api_v1/endpoints/`
5. **Add to router** in `app/api/api_v1/api.py`

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Security

- JWT tokens for authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation with Pydantic
- SQL injection protection via SQLAlchemy ORM

## Performance

- Async/await for I/O operations
- Database connection pooling
- Vector indexing for fast search
- Efficient query optimization
- Response caching for static data

## Monitoring

- Health check endpoint: `GET /health`
- Structured logging
- Error tracking and reporting
- Performance metrics

## License

MIT License - see LICENSE file for details.
