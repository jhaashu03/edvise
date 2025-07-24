# SECURITY NOTICE - CRITICAL CONFIGURATION FILE ISSUE

⚠️ **IMPORTANT**: The original `prepgenie/backend/app/core/config.py` file contained hardcoded sensitive credentials including:

- Milvus/Zilliz authentication tokens
- Walmart LLM Gateway API keys 
- Private keys and consumer IDs

## Action Taken:
1. Added `**/config.py` to `.gitignore` to prevent committing sensitive configuration
2. Created `config_template.py` as a clean template without hardcoded secrets
3. Updated `.env.example` to show proper environment variable structure

## Before deploying:
1. Copy `config_template.py` to `config.py`
2. Set up proper environment variables in `.env` file
3. Never commit files with hardcoded API keys, tokens, or secrets

## Security Best Practices:
- All sensitive configuration should be loaded from environment variables
- Use `.env` files locally (never commit them)
- Use proper secret management in production (Azure Key Vault, AWS Secrets Manager, etc.)
