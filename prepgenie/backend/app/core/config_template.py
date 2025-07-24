from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Union
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PrepGenie API"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://prepgenie-frontend.vercel.app"
    ]
    
    # Database - Supabase PostgreSQL using separate environment variables
    DB_USER: str = os.getenv("user", "postgres")
    DB_PASSWORD: str = os.getenv("password", "")
    DB_HOST: str = os.getenv("host", "localhost")
    DB_PORT: str = os.getenv("port", "5432")
    DB_NAME: str = os.getenv("dbname", "prepgenie")
    
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
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # LLM Provider Selection
    LLM_PROVIDER: str = "openai"  # "openai", "walmart_gateway", or "ollama"
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    # Walmart LLM Gateway - ALL VALUES LOADED FROM ENVIRONMENT
    WALMART_LLM_GATEWAY_API_KEY: str = os.getenv("WALMART_LLM_GATEWAY_API_KEY", "")
    WALMART_LLM_GATEWAY_BASE_URL: str = os.getenv("WALMART_LLM_GATEWAY_BASE_URL", "https://wmtllmgateway.stage.walmart.com/wmtllmgateway")
    WALMART_LLM_GATEWAY_MODEL: str = os.getenv("WALMART_LLM_GATEWAY_MODEL", "gpt-4.1-mini")
    WALMART_LLM_GATEWAY_SVC_ENV: str = os.getenv("WALMART_LLM_GATEWAY_SVC_ENV", "stage")
    
    # Consumer Auth (if using private key auth instead of API key)
    WALMART_CONSUMER_ID: str = os.getenv("WALMART_CONSUMER_ID", "")
    WALMART_PRIVATE_KEY: str = os.getenv("WALMART_PRIVATE_KEY", "")
    
    # Zilliz (Milvus Cloud) and local Milvus Lite - ALL VALUES LOADED FROM ENVIRONMENT
    MILVUS_URI: str = os.getenv("MILVUS_URI", "https://localhost:19530")  # Default to local
    MILVUS_TOKEN: str = os.getenv("MILVUS_TOKEN", "")  # MUST be set via environment
    MILVUS_LOCAL_PATH: str = os.getenv("MILVUS_LOCAL_PATH", "./milvus_lite_local.db")
    
    # Vector service control
    DISABLE_VECTOR_SERVICE: bool = os.getenv("DISABLE_VECTOR_SERVICE", "false").lower() in ("true", "1", "yes")
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # LLM Gateway Configuration - ALL SENSITIVE DATA LOADED FROM ENVIRONMENT
    LLM_GATEWAY_CONFIG: dict = {
        "model_to_use": {
            "name": "gpt-4o",
            "model_version": "2024-08-06",
            "api_version": "2024-02-01"
        },
        "retry": {
            "max_retries": 2,
            "min_wait_time": 3,
            "max_wait_time": 30
        },
        # Consumers config loaded from environment to avoid hardcoded secrets
        "consumers": []  # Populated dynamically from environment variables
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Dynamically populate LLM Gateway consumers from environment
        if self.WALMART_CONSUMER_ID and self.WALMART_PRIVATE_KEY:
            self.LLM_GATEWAY_CONFIG["consumers"] = [
                {
                    "base_url_openai_proxy": os.getenv("WALMART_GATEWAY_BASE_URL", "https://wmtllmgateway.prod.walmart.com/wmtllmgateway"),
                    "consumer_id": self.WALMART_CONSUMER_ID,
                    "private_key": self.WALMART_PRIVATE_KEY,
                    "model": "gpt-4o",
                    "environment": "prod",
                    "service_env": "prod"
                }
            ]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
