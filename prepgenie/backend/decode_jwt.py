#!/usr/bin/env python3
"""
JWT decoder to understand the API key structure
"""

import json
import base64

def decode_jwt(token):
    """Decode JWT token to see its contents"""
    try:
        # Split the JWT into parts
        header, payload, signature = token.split('.')
        
        # Add padding if needed
        header += '=' * (4 - len(header) % 4)
        payload += '=' * (4 - len(payload) % 4)
        
        # Decode header and payload
        header_data = json.loads(base64.b64decode(header))
        payload_data = json.loads(base64.b64decode(payload))
        
        return header_data, payload_data
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None, None

if __name__ == "__main__":
    api_key = "eyJzZ252ZXIiOiIxIiwiYWxnIjoiSFMyNTYiLCJ0eXAiOiJKV1QifQ.eyJqdGkiOiIyNDAyIiwic3ViIjoiNjcyIiwiaXNzIjoiV01UTExNR0FURVdBWS1TVEciLCJhY3QiOiJiMHQwNW90IiwidHlwZSI6IkFQUCIsImlhdCI6MTc1MDc5NjMyNywiZXhwIjoxNzY2MzQ4MzI3fQ.uYkVeTmOodg_ya2rqbXAFh3NIc_nlCCJJsqhDZwualQ"
    
    header, payload = decode_jwt(api_key)
    
    if header and payload:
        print("JWT Header:")
        print(json.dumps(header, indent=2))
        print("\nJWT Payload:")
        print(json.dumps(payload, indent=2))
        
        # Look for consumer-related fields
        print("\nPossible Consumer ID fields:")
        for key, value in payload.items():
            if 'sub' in key.lower() or 'consumer' in key.lower() or 'client' in key.lower():
                print(f"  {key}: {value}")
