# Ollama Integration for PrepGenie

This document explains how to use Ollama as the LLM provider for PrepGenie instead of OpenAI.

## ✅ What's Been Done

1. **Added Ollama Provider**: Created `OllamaProvider` class in `app/core/llm_service.py`
2. **Updated Configuration**: Added Ollama settings to `app/core/config.py`
3. **Environment Setup**: Updated `.env.local` to use Ollama by default
4. **API Endpoints**: Existing FastAPI endpoints now work with Ollama
5. **Comprehensive Testing**: Created multiple test scripts to validate integration

## 🚀 Quick Start

### 1. Install and Start Ollama

```bash
# Install Ollama (if not already installed)
# Download from: https://ollama.ai

# Start Ollama server
ollama serve

# Pull the model (in another terminal)
ollama pull tinyllama
```

### 2. Configure Environment

Your `.env.local` file is already configured with:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama
```

### 3. Test the Integration

```bash
# Test Ollama service directly
python test_ollama_integration.py

# Start FastAPI server and test endpoints
python test_server_quick.py

# Or test with curl (server must be running)
./test_curl.sh
```

## 📡 API Endpoints

All existing LLM endpoints now work with Ollama:

### 1. Simple Chat
```bash
curl -X POST 'http://localhost:8000/api/v1/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is the capital of France?",
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

### 2. Conversation (with history)
```bash
curl -X POST 'http://localhost:8000/api/v1/conversation' \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"},
      {"role": "assistant", "content": "Hi there!"},
      {"role": "user", "content": "How are you?"}
    ],
    "temperature": 0.7
  }'
```

### 3. LLM Status
```bash
curl -X GET 'http://localhost:8000/api/v1/llm/status'
```

### 4. UPSC Question Analysis
```bash
curl -X POST 'http://localhost:8000/api/v1/upsc/analyze-question?question=What is democracy?'
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Set to `ollama` to use Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `tinyllama` | Model to use |

### Supported Models

You can use any model available in Ollama:

```bash
# List available models
ollama list

# Pull different models
ollama pull llama2
ollama pull codellama
ollama pull mistral

# Update config to use different model
# Set OLLAMA_MODEL=llama2 in .env.local
```

## 🧪 Testing Scripts

### 1. `test_ollama_integration.py`
- Tests Ollama direct API
- Tests LLM service integration  
- Tests conversation flow
- Lists available models

### 2. `test_server_quick.py`
- Starts FastAPI server automatically
- Runs quick health checks
- Provides manual testing commands

### 3. `test_api_endpoints.py`
- Tests all FastAPI endpoints
- Shows curl command examples

### 4. `test_curl.sh`
- Bash script for manual testing
- Uses curl commands directly

## 🎯 Usage in Your Java App

Since you mentioned Java, here's how you'd call the API from Java:

```java
// Using your existing HTTP client
RestTemplate restTemplate = new RestTemplate();

// Simple chat request
ChatRequest request = new ChatRequest();
request.setMessage("What is machine learning?");
request.setTemperature(0.7);

HttpHeaders headers = new HttpHeaders();
headers.setContentType(MediaType.APPLICATION_JSON);
HttpEntity<ChatRequest> entity = new HttpEntity<>(request, headers);

ResponseEntity<ChatResponse> response = restTemplate.postForEntity(
    "http://localhost:8000/api/v1/chat", 
    entity, 
    ChatResponse.class
);

String aiResponse = response.getBody().getResponse();
```

## 🔀 Switching Between Providers

You can easily switch between providers by changing the `LLM_PROVIDER` environment variable:

```env
# Use Ollama (local)
LLM_PROVIDER=ollama

# Use OpenAI (requires API key)
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# Use Walmart Gateway (if configured)
LLM_PROVIDER=walmart_gateway
```

## 📊 Performance Notes

- **Ollama**: Local, private, free, but slower than cloud APIs
- **Response Time**: Depends on your hardware (GPU recommended)
- **Model Size**: tinyllama is fast but less capable; llama2/mistral are slower but better
- **Memory Usage**: Larger models require more RAM

## 🚨 Troubleshooting

### Ollama Not Responding
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Model Not Found
```bash
# List models
ollama list

# Pull missing model
ollama pull tinyllama
```

### API Endpoint Errors
```bash
# Check server logs
python -m uvicorn app.main:app --reload --log-level debug

# Test configuration
python test_ollama_integration.py
```

### Performance Issues
- Use smaller models (tinyllama, mistral-7b)
- Consider GPU acceleration if available
- Adjust model parameters (temperature, max_tokens)

## 🎉 Benefits of Ollama Integration

1. **Privacy**: All processing happens locally
2. **Cost**: No API fees
3. **Availability**: Works offline
4. **Control**: Full control over models and parameters
5. **Flexibility**: Easy to switch models or providers

## 📝 Next Steps

1. Test with different Ollama models
2. Optimize performance for your hardware
3. Consider deploying Ollama on a dedicated server
4. Implement model-specific optimizations
5. Add model management endpoints

The integration is complete and ready to use! 🚀
