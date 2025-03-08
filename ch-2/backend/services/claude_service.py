import os
import json
import requests
import logging
from fastapi import HTTPException
import base64
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

class ClaudeService:
    def __init__(self):
        self.api_key = CLAUDE_API_KEY
        if not self.api_key:
            raise ValueError("Claude API key not set")
        self.model = "claude-3-opus-20240229"  # Default to opus, can be changed
        
        logger.info(f"Claude service initialized with model: {self.model}")
    
    def generate_response(self, messages):
        """Generate a response from Claude using the anthropic API directly"""
        try:
            # Format the conversation history for Claude
            # Claude expects a different format than OpenAI
            formatted_messages = []
            
            # Debug the incoming messages
            logger.debug(f"Claude received messages: {json.dumps(messages[:2])}...")
            
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                content = msg["content"]
                
                # Check if the content might contain an image
                if isinstance(content, list):
                    # This is a multimodal message, we need to extract the text part
                    text_parts = []
                    for part in content:
                        if part.get("type") == "text":
                            text_parts.append(part["text"])
                    content = " ".join(text_parts)
                
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
            
            url = "https://api.anthropic.com/v1/messages"
            
            # Instructions for Claude - make it clearly identify as Claude
            system_prompt = "You are Claude, an AI assistant by Anthropic. Always make it clear that you are Claude in your responses. Be helpful, concise, and clear."
            
            payload = {
                "model": self.model,
                "system": system_prompt,
                "messages": formatted_messages,
                "max_tokens": 2000
            }
            
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            logger.info(f"Sending request to Claude API with {len(formatted_messages)} messages")
            
            # Debug output the actual request payload
            logger.debug(f"Claude API request payload: {json.dumps(payload)[:500]}...")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Debug the response structure
            logger.debug(f"Claude API response structure: {list(result.keys())}")
            
            if "content" in result and result["content"]:
                # Extract text from the content array
                text_content = ""
                for item in result["content"]:
                    if item["type"] == "text":
                        text_content += item["text"]
                        
                logger.info(f"Claude API returned {len(text_content)} chars")
                
                # Ensure the response clearly identifies as Claude
                if not any(marker in text_content.lower() for marker in ["claude", "anthropic", "as claude", "i'm claude"]):
                    text_content = "As Claude, I'll address your question: " + text_content
                
                return text_content
            else:
                logger.error("Claude API returned invalid response format")
                return "As Claude, I apologize, but I'm having trouble generating a response right now."
                
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            # Try to extract more details from the response if available
            response_text = getattr(e, 'response', None)
            if response_text:
                try:
                    response_data = response_text.json()
                    logger.error(f"Claude API error details: {response_data}")
                except:
                    pass
                    
            raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")
    
    def analyze_image(self, image_base64):
        """Process an image with Claude and return a description"""
        try:
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Validate image_base64 is a string
            if not isinstance(image_base64, str):
                logger.error("Image data must be a base64-encoded string")
                return "Unable to analyze the image: invalid format"
            
            # Convert base64 to Claude's expected message format
            payload = {
                "model": self.model,
                "system": "You are Claude, an AI assistant by Anthropic skilled at analyzing images. Always identify yourself as Claude in your responses.",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": "Describe this image in detail. What do you see?"
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            logger.info("Sending image analysis request to Claude API")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Fixed the syntax error here - removed extra ]
            if "content" in result and result["content"]:
                # Extract text from the content array
                text_content = ""
                for item in result["content"]:
                    if item["type"] == "text":
                        text_content += item["text"]
                        
                logger.info(f"Claude image analysis returned {len(text_content)} chars")
                
                # Add Claude signature if it doesn't have one
                if not text_content.lower().startswith("as claude"):
                    text_content = "As Claude, I can see that this image shows " + text_content
                    
                return text_content
            else:
                logger.error("Claude API returned invalid response format for image analysis")
                return "As Claude, I apologize, but I'm having trouble analyzing this image right now."
                
        except Exception as e:
            logger.error(f"Claude image analysis error: {str(e)}")
            return f"As Claude, I'm unable to analyze the image: {str(e)[:100]}"
