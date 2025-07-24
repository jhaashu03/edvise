"""
Unified LLM Service supporting both OpenAI and Walmart LLM Gateway
"""

import asyncio
import json
import logging
import os
import time
import hashlib
import hmac
import base64
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel
import httpx
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt

from app.core.config import settings
from app.utils.rate_limit_handler import with_rate_limit, rate_limit_handler

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Exception raised when hitting rate limits (429)"""
    pass


class LLMServiceError(Exception):
    """Base exception for LLM service errors"""
    pass


class ChatMessage(BaseModel):
    """Chat message format"""
    role: str  # "user", "assistant", "system"
    content: str


class ChatResponse(BaseModel):
    """Unified response format"""
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: str
    provider: str


def generate_walmart_auth_signature(consumer_id: str, private_key: str) -> tuple[str, str, str]:
    """Generate authentication signature for Walmart LLM Gateway"""
    timestamp = str(int(time.time() * 1000))
    key_version = "1"
    
    # Create the string to sign
    string_to_sign = f"{consumer_id}\n{timestamp}\n{key_version}\n"
    
    try:
        # Decode the private key
        private_key_bytes = base64.b64decode(private_key)
        
        # Create HMAC signature
        signature = hmac.new(
            private_key_bytes,
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        )
        
        # Base64 encode the signature
        auth_sig = base64.b64encode(signature.digest()).decode('utf-8')
        
        return timestamp, auth_sig, key_version
    except Exception as e:
        logger.error(f"Failed to generate auth signature: {e}")
        raise


class OpenAIProvider:
    """OpenAI API provider"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_MODEL
        
        if not self.api_key:
            raise LLMServiceError("OpenAI API key not configured")
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitException)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3)
    )
    @with_rate_limit
    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Send chat completion request to OpenAI"""
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": kwargs.get("temperature", 0),
            "max_tokens": kwargs.get("max_tokens", 3200),
            "top_p": kwargs.get("top_p", 0.01),
            "frequency_penalty": kwargs.get("frequency_penalty", 0),
            "presence_penalty": kwargs.get("presence_penalty", 0)
        }
        
        # Check if we're using Walmart Gateway (based on URL)
        if "wmtllmgateway" in self.base_url.lower():
            # Use Walmart Gateway format with correct headers
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "PrepGenie/1.0",
                "X-UPSTREAM": "WMTLLMGATEWAY.GenAI.Api",
                "X-ACTION": "LLMQuery"
            }
        else:
            # Use standard OpenAI format
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        
        # For stage environment, bypass SSL verification
        verify_ssl = "stage" not in self.base_url.lower()
        
        async with httpx.AsyncClient(timeout=60.0, verify=verify_ssl) as client:
            try:
                # Construct URL with API version for Walmart Gateway deployments
                if "wmtllmgateway" in self.base_url.lower() and "deployments" in self.base_url.lower():
                    url = f"{self.base_url}/chat/completions?api-version=2024-02-01"
                else:
                    url = f"{self.base_url}/chat/completions"
                
                logger.info(f"Sending request to OpenAI: {url}")
                logger.debug(f"Headers: {headers}")
                logger.debug(f"Payload: {payload}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 429:
                    raise RateLimitException("OpenAI rate limit exceeded")
                
                response.raise_for_status()
                response_data = response.json()
                
                logger.info(f"OpenAI response status: {response.status_code}")
                
                # Extract content from response
                content = ""
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    content = response_data["choices"][0].get("message", {}).get("content", "")
                
                return ChatResponse(
                    content=content,
                    usage=response_data.get("usage"),
                    model=response_data.get("model", self.model),
                    provider="openai"
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"OpenAI API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"OpenAI request error: {e}")
                raise LLMServiceError(f"OpenAI error: {str(e)}")

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitException)),
        wait=wait_exponential(multiplier=1, min=3, max=30),
        stop=stop_after_attempt(2)
    )
    @with_rate_limit
    async def vision_completion(self, messages: List[Dict], **kwargs) -> str:
        """Send vision completion request to OpenAI (supports images)"""
        
        payload = {
            "model": kwargs.get("model", "gpt-4-vision-preview"),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }
        
        # Check if we're using Walmart Gateway (based on URL)
        if "wmtllmgateway" in self.base_url.lower():
            # Use Walmart Gateway format with correct headers
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "PrepGenie/1.0",
                "X-UPSTREAM": "WMTLLMGATEWAY.GenAI.Api",
                "X-ACTION": "LLMQuery"
            }
        else:
            # Use standard OpenAI format
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        
        # For stage environment, bypass SSL verification
        verify_ssl = "stage" not in self.base_url.lower()
        
        async with httpx.AsyncClient(timeout=120.0, verify=verify_ssl) as client:
            try:
                # Construct URL with API version for Walmart Gateway deployments
                if "wmtllmgateway" in self.base_url.lower() and "deployments" in self.base_url.lower():
                    url = f"{self.base_url}/chat/completions?api-version=2024-02-01"
                else:
                    url = f"{self.base_url}/chat/completions"
                
                logger.info(f"Sending vision request to OpenAI: {url}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 429:
                    raise RateLimitException("OpenAI rate limit exceeded")
                
                response.raise_for_status()
                response_data = response.json()
                
                logger.info(f"OpenAI vision response status: {response.status_code}")
                
                # Extract content from response
                content = ""
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    content = response_data["choices"][0].get("message", {}).get("content", "")
                
                return content
                
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI Vision HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"OpenAI Vision API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"OpenAI Vision request error: {e}")
                raise LLMServiceError(f"OpenAI Vision error: {str(e)}")


class WalmartLLMGatewayProvider:
    """Walmart LLM Gateway provider"""
    
    def __init__(self):
        # Configuration based on the provided config
        self.use_api_key = bool(settings.WALMART_LLM_GATEWAY_API_KEY)
        
        if self.use_api_key:
            self.api_key = settings.WALMART_LLM_GATEWAY_API_KEY
            self.base_url = settings.WALMART_LLM_GATEWAY_BASE_URL or "https://wmtllmgateway.stage.walmart.com/wmtllmgateway"
            self.model = settings.WALMART_LLM_GATEWAY_MODEL or "gpt-4.1-mini"
            self.svc_env = settings.WALMART_LLM_GATEWAY_SVC_ENV or "stage"
            self.consumer_id = "672"  # From JWT sub field
        else:
            # Use consumer auth
            self.consumer_id = settings.WALMART_CONSUMER_ID
            self.private_key = settings.WALMART_PRIVATE_KEY
            self.base_url = settings.WALMART_LLM_GATEWAY_BASE_URL or "https://wmtllmgateway.stage.walmart.com/wmtllmgateway"
            self.model = settings.WALMART_LLM_GATEWAY_MODEL or "gpt-4.1-mini"
            self.svc_env = settings.WALMART_LLM_GATEWAY_SVC_ENV or "stage"
            
            if not self.consumer_id or not self.private_key:
                raise LLMServiceError("Walmart LLM Gateway credentials not configured")
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitException)),
        wait=wait_exponential(multiplier=1, min=3, max=30),
        stop=stop_after_attempt(2)
    )
    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Send chat completion request to Walmart LLM Gateway"""
        
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "temperature": kwargs.get("temperature", 0),
            "max_tokens": kwargs.get("max_tokens", 3200),
            "top_p": kwargs.get("top_p", 0.01),
            "frequency_penalty": kwargs.get("frequency_penalty", 0),
            "presence_penalty": kwargs.get("presence_penalty", 0)
        }
        
        # Prepare headers based on auth method
        if self.use_api_key:
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "PrepGenie/1.0",
                "WM_CONSUMER.ID": os.getenv("WALMART_CONSUMER_ID", ""),  # Required for routing
                "WM_SVC.NAME": "WMTLLMGATEWAY", 
                "WM_SVC.ENV": self.svc_env,
                "X-UPSTREAM": "WMTLLMGATEWAY.GenAI.Api",
                "X-ACTION": "LLMQuery"
            }
        else:
            # Consumer auth
            timestamp, auth_sig, key_version = generate_walmart_auth_signature(
                self.consumer_id, self.private_key
            )
            headers = {
                "Content-Type": "application/json",
                "WM_CONSUMER.ID": self.consumer_id,
                "WM_SVC.NAME": "WMTLLMGATEWAY",
                "WM_SVC.ENV": self.svc_env,
                "WM_CONSUMER.INTIMESTAMP": timestamp,
                "WM_SEC.KEY_VERSION": key_version,
                "WM_SEC.AUTH_SIGNATURE": auth_sig,
                "X-UPSTREAM": "WMTLLMGATEWAY.GenAI.Api",
                "X-ACTION": "LLMQuery"
            }
        
        # Construct URL - Use direct path for all cases
        url = f"{self.base_url}/chat/completions"
        
        # For stage environment, bypass SSL verification
        verify_ssl = self.svc_env != "stage"
        
        async with httpx.AsyncClient(timeout=60.0, verify=verify_ssl) as client:
            try:
                logger.info(f"Sending request to Walmart LLM Gateway: {url}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 429:
                    raise RateLimitException("Walmart LLM Gateway rate limit exceeded")
                
                response.raise_for_status()
                response_data = response.json()
                
                logger.info(f"Walmart LLM Gateway response status: {response.status_code}")
                
                # Extract content from response
                content = ""
                if response_data.get("choices") and len(response_data["choices"]) > 0:
                    content = response_data["choices"][0].get("message", {}).get("content", "")
                
                return ChatResponse(
                    content=content,
                    usage=response_data.get("usage"),
                    model=response_data.get("model", self.model),
                    provider="walmart_gateway"
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Walmart LLM Gateway HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"Walmart LLM Gateway error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Walmart LLM Gateway request error: {e}")
                raise LLMServiceError(f"Walmart LLM Gateway error: {str(e)}")


class OllamaProvider:
    """Provider for Ollama local LLM service"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        
        if not self.base_url:
            raise LLMServiceError("Ollama base URL not configured")
        
        logger.info(f"Initialized Ollama provider with base_url: {self.base_url}, model: {self.model}")
    
    @retry(
        retry=retry_if_exception_type((RateLimitException, httpx.RequestError)),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3)
    )
    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Send chat completion request to Ollama"""
        
        # Convert messages to a single prompt for Ollama
        prompt = self._convert_messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 1.0),
                "num_predict": kwargs.get("max_tokens", 1000)
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 429:
                    raise RateLimitException("Ollama rate limit exceeded")
                
                response.raise_for_status()
                result = response.json()
                
                return ChatResponse(
                    content=result.get("response", ""),
                    model=self.model,
                    provider="ollama",
                    usage={
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                    }
                )
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"Ollama error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Ollama request error: {e}")
                raise LLMServiceError(f"Ollama error: {str(e)}")
    
    def _convert_messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert chat messages to a single prompt for Ollama"""
        prompt_parts = []
        
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}")
            elif message.role == "user":
                prompt_parts.append(f"User: {message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"Assistant: {message.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)


class LLMService:
    """Unified LLM service that can use OpenAI, Walmart LLM Gateway, or Ollama"""
    
    def __init__(self):
        self.provider_name = settings.LLM_PROVIDER.lower()
        
        if self.provider_name == "openai":
            self.provider = OpenAIProvider()
        elif self.provider_name == "walmart_gateway":
            self.provider = WalmartLLMGatewayProvider()
        elif self.provider_name == "ollama":
            self.provider = OllamaProvider()
        else:
            raise LLMServiceError(f"Unsupported LLM provider: {self.provider_name}")
        
        logger.info(f"Initialized LLM service with provider: {self.provider_name}")
    
    async def chat_completion(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Send chat completion request using the configured provider"""
        return await self.provider.chat_completion(messages, **kwargs)
    
    async def simple_chat(self, user_message: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Simple chat interface that returns just the response text"""
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        messages.append(ChatMessage(role="user", content=user_message))
        
        response = await self.chat_completion(messages, **kwargs)
        return response.content
    
    async def vision_chat(self, messages: List[Dict], **kwargs) -> str:
        """Vision chat interface for image analysis (OpenAI-style)"""
        if self.provider_name != "openai":
            raise LLMServiceError(f"Vision chat not supported by provider: {self.provider_name}")
        
        # For OpenAI provider, call the vision endpoint directly
        return await self.provider.vision_completion(messages, **kwargs)
    
    async def generate_completion(self, prompt: str, **kwargs) -> str:
        """Generate a simple completion for a given prompt (Ollama-style interface)"""
        return await self.simple_chat(prompt, **kwargs)


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance"""
    global _llm_service
    # For development, always create new instance to pick up config changes
    if settings.ENVIRONMENT == "local":
        return LLMService()
    
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# Test function
async def test_llm_service():
    """Test the LLM service with the configured provider"""
    try:
        llm = get_llm_service()
        
        response = await llm.simple_chat(
            user_message="Hello! Can you explain what UPSC is in one sentence?",
            system_prompt="You are a helpful AI assistant specializing in UPSC (Union Public Service Commission) exam preparation."
        )
        
        print(f"✅ LLM service test successful with provider: {llm.provider_name}")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test
    asyncio.run(test_llm_service())
