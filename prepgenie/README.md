# PrepGenie: Your Personalized UPSC AI Mentor

🎯 **Goal**: Help UPSC aspirants prepare smarter with personalized study plans, AI-based PYQ search, mock answer evaluation, and comprehensive access to official resources.

## Features

- 🔐 **User Authentication** - Secure JWT-based authentication
- 📚 **UPSC Content Hub** - Access to syllabus, PYQs, toppers' answers
- 🔍 **Smart PYQ Search** - RAG-powered semantic search
- 🧑‍🏫 **Answer Evaluation** - AI-powered feedback and scoring
- 📅 **Study Planner** - Personalized preparation schedules
- 📊 **Progress Tracking** - Comprehensive analytics dashboard
- 💬 **AI Chatbot** - UPSC-focused Q&A assistance

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TailwindCSS |
| Backend | FastAPI |
| Vector DB | Milvus (Zilliz Cloud) |
| Database | PostgreSQL (Railway) |
| Authentication | JWT-based |
| AI Model | OpenAI GPT-4-turbo |
| Deployment | Vercel (Frontend), Railway (Backend) |

## Project Structure

```
prepgenie/
├── frontend/          # React + TailwindCSS app
├── backend/           # FastAPI application
├── docs/              # Documentation
└── README.md
```

## Quick Start

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost/prepgenie
OPENAI_API_KEY=your_openai_key
MILVUS_URL=your_milvus_url
MILVUS_TOKEN=your_milvus_token
JWT_SECRET_KEY=your_secret_key
```

## Deployment

- **Frontend**: Deploy to Vercel
- **Backend**: Deploy to Railway
- **Database**: PostgreSQL on Railway
- **Vector DB**: Zilliz Cloud

## License

MIT License
