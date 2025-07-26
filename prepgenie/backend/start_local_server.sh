#!/bin/bash
cd /Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend
# Use local development environment (loads from .env file)
ENVIRONMENT=development PYTHONPATH=/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
