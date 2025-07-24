#!/bin/bash
cd prepgenie/backend
uvicorn main:app --reload --port 8000
