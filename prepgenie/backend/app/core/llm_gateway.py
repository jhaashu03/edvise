"""
Walmart LLM Gateway Integration
Based on: https://gecgithub01.walmart.com/SAMFCC/fusion-proctor/blob/develop/app/core/llm_gateway/llm_gateway.py
"""

import httpx
import asyncio
import json
import logging
import time
import hashlib
import hmac
import base64
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, wait_random, stop_after_attempt, RetryCallState

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Exception raised when hitting rate limits (429)"""
    pass


def before_retry_log(retry_state: RetryCallState) -> None:
    """Log retry attempts with safe access to retry state"""
    try:
        sleep_time = (
            retry_state.next_action.sleep
            if retry_state.next_action and hasattr(retry_state.next_action, 'sleep')
            else 'unknown'
        )
        logger.warning(
            "Rate limit hit, retrying",
            extra={
                "attempt_number": retry_state.attempt_number,
                "sleep_time": sleep_time,
                "retry_object": str(retry_state.outcome) if retry_state.outcome else "No outcome available",
            },
        )
    except Exception as e:
        logger.warning(
            "Rate limit hit, retrying (retry state details unavailable)",
            extra={"error": str(e), "retry_state_available": bool(retry_state)}
        )


def generate_auth_signature(consumer_id: str, private_key: str) -> tuple[str, str, str]:
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


class ConsumerAuth(BaseModel):
    """Authentication using consumer ID and private key"""
    consumer_id: str
    private_key: str


class ApiKeyAuth(BaseModel):
    """Authentication using API key"""
    api_key: str


AuthType = Union[ConsumerAuth, ApiKeyAuth]


class LLMGatewayConfig(BaseModel):
    """Configuration for Walmart LLM Gateway"""
    # Auth can be either consumer auth or API key auth
    auth: AuthType
    base_url_openai_proxy: str
    model: str
    svc_env: str
    model_parameters: Dict[str, Any]
    # Retry configuration
    max_retries: int = 2
    min_wait_time: int = 3
    max_wait_time: int = 30


class ChatMessage(BaseModel):
    """Chat message format for LLM Gateway"""
    role: str  # "user", "assistant", "system"
    content: str


class ChatResponse(BaseModel):
    """Response from LLM Gateway"""
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    model: str

class ChatResponse(BaseModel):
    """Response from LLM Gateway"""
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    model: str
    
class LLMGateway:
    """Walmart LLM Gateway client"""
    
    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        
        # For stage environment, we may need to bypass SSL verification
        verify_ssl = config.svc_env != "stage"
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),  # 60 second timeout
            verify=verify_ssl,  # Bypass SSL verification for stage
            headers={
                "X-API-KEY": config.api_key,
                "Content-Type": "application/json",
                "User-Agent": "PrepGenie/1.0",
                # Walmart mandatory routing headers - use exact expected values
                "WM_CONSUMER.ID": "aff5571e-8fa9-4cb3-9981-eb361e4ff53e",
                "wm_svc.name": "WMTLLMGATEWAY",  # Use exact expected value
                "wm_svc.env": config.svc_env     # Should be "stage"
            }
        )
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage],
        **kwargs
    ) -> ChatResponse:
        """
        Send chat completion request to Walmart LLM Gateway
        """
        # Prepare the request payload
        payload = {
            "model": self.config.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            **self.config.model_parameters,
            **kwargs  # Allow override of model parameters
        }
        
        # Construct the URL - try different path variations
        url = f"{self.config.base_url_openai_proxy}/chat/completions"  # Remove /v1 prefix
        
        try:
            logger.info(f"Sending request to LLM Gateway: {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            logger.info(f"LLM Gateway response status: {response.status_code}")
            logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
            
            return ChatResponse(**response_data)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM Gateway: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM Gateway HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error to LLM Gateway: {e}")
            raise Exception(f"LLM Gateway request error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error with LLM Gateway: {e}")
            raise Exception(f"LLM Gateway error: {str(e)}")
    
    async def simple_chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        Simple chat interface that returns just the response text
        """
        messages = []
        
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
            
        messages.append(ChatMessage(role="user", content=user_message))
        
        response = await self.chat_completion(messages)
        
        if response.choices and len(response.choices) > 0:
            return response.choices[0].get("message", {}).get("content", "")
        else:
            raise Exception("No response from LLM Gateway")

# Global configuration - you can modify these values
DEFAULT_LLM_CONFIG = LLMGatewayConfig(
    api_key="eyJzZ252ZXIiOiIxIiwiYWxnIjoiSFMyNTYiLCJ0eXAiOiJKV1QifQ.eyJqdGkiOiIyNDAyIiwic3ViIjoiNjcyIiwiaXNzIjoiV01UTExNR0FURVdBWS1TVEciLCJhY3QiOiJiMHQwNW90IiwidHlwZSI6IkFQUCIsImlhdCI6MTc1MDc5NjMyNywiZXhwIjoxNzY2MzQ4MzI3fQ.uYkVeTmOodg_ya2rqbXAFh3NIc_nlCCJJsqhDZwualQ",
    base_url_openai_proxy="https://wmtllmgateway.stage.walmart.com/wmtllmgateway",
    model="gpt-4.1-mini",
    svc_env="stage",
    model_parameters={
        "temperature": 0,
        "max_tokens": 3200,
        "top_p": 0.01,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
)

async def get_llm_gateway() -> LLMGateway:
    """Factory function to create LLM Gateway instance"""
    return LLMGateway(DEFAULT_LLM_CONFIG)

# Test function
async def test_llm_gateway():
    """Test the LLM Gateway integration"""
    async with LLMGateway(DEFAULT_LLM_CONFIG) as gateway:
        try:
            response = await gateway.simple_chat(
                user_message="Hello! Can you explain what UPSC is in one sentence?",
                system_prompt="You are a helpful AI assistant specializing in UPSC (Union Public Service Commission) exam preparation."
            )
            print(f"✅ LLM Gateway test successful!")
            print(f"Response: {response}")
            return True
        except Exception as e:
            print(f"❌ LLM Gateway test failed: {e}")
            return False

if __name__ == "__main__":
    # Run test
    asyncio.run(test_llm_gateway())
