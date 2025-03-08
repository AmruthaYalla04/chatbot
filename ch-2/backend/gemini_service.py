import logging
import requests
import json
import os
import traceback
import time
from alternatives import get_rule_based_response

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")

class GeminiService:
    """Service class to handle Google Gemini API interactions"""
    
    def __init__(self, api_key=None):
        # Use provided API key or fallback to our known working key
        self.api_key = api_key or GEMINI_API_KEY
        
        # Set default API version and model based on the working curl example
        self.api_version = "v1beta"
        self.model = "gemini-2.0-flash"  # Use the model from the curl example
        
        logger.info(f"Gemini service initializing with API version: {self.api_version}, model: {self.model}")
        logger.info(f"Using API key: {self.api_key[:5]}...{self.api_key[-4:]}")
        
        # Initialize requests session for connection pooling
        self.session = requests.Session()
        
        # Test the connection on startup
        self._test_connection()
    
    def _test_connection(self):
        """Test the API connection silently"""
        if not self.api_key:
            logger.warning("No Gemini API key provided - will use fallbacks")
            return False
        
        # Use the exact URL format from the curl example
        url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Hello"
                        }
                    ]
                }
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            logger.info(f"Testing Gemini API connection with URL: {url.split('?')[0]}")
            response = self.session.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Gemini API connection successful")
                return True
            else:
                logger.warning(f"⚠️ Gemini API connection failed with status code: {response.status_code}")
                
                # Try to parse error information
                try:
                    error_info = response.json()
                    logger.warning(f"Error details: {json.dumps(error_info)}")
                    
                    # Try with fallback model if this one doesn't work
                    if "NOT_FOUND" in str(error_info):
                        return self._try_fallback_model()
                except:
                    logger.warning(f"Raw response: {response.text[:200]}")
                    
                return False
        except Exception as e:
            logger.warning(f"⚠️ Gemini API connection test failed: {str(e)}")
            return self._try_fallback_model()
    
    def _try_fallback_model(self):
        """Try connection with fallback models if the main one fails"""
        # List of fallback models to try
        fallback_models = [
            "gemini-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
        
        for model in fallback_models:
            try:
                logger.info(f"Trying fallback model: {model}")
                url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{model}:generateContent?key={self.api_key}"
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Hello"
                                }
                            ]
                        }
                    ]
                }
                
                headers = {"Content-Type": "application/json"}
                response = self.session.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ Fallback model {model} works! Using this instead.")
                    self.model = model
                    return True
            except Exception as e:
                logger.warning(f"Fallback model {model} failed: {str(e)}")
                continue
        
        logger.error("❌ All Gemini models failed, will use rule-based fallbacks")
        return False
    
    def generate_response(self, conversation_history):
        """Generate a response using Google Gemini API with the correct API structure"""
        # Check for valid API key
        if not self.api_key:
            logger.error("Invalid or missing Gemini API key")
            return "I apologize, but I can't connect to Gemini due to an invalid API key."
            
        try:
            # Log that we're using Gemini
            logger.info(f"Using Gemini model: {self.model}")
            
            # Format the conversation history to match Gemini API structure
            # The API expects a specific format for the conversation
            formatted_parts = []
            
            # Add the conversation history
            user_message = ""
            for msg in conversation_history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                # Store the most recent user message for simpler prompt if needed
                if role == 'user':
                    user_message = content
                
                # Add to formatted parts
                formatted_parts.append({
                    "text": f"{role}: {content}\n"
                })
            
            # Add final instruction to identify as Gemini
            formatted_parts.append({
                "text": "Please respond as Gemini AI developed by Google."
            })
            
            # Create the exact payload structure from the curl example
            payload = {
                "contents": [
                    {
                        "parts": formatted_parts
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 800,
                    "topP": 0.95
                }
            }
            
            # Use the exact URL format from the curl example
            url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{self.model}:generateContent?key={self.api_key}"
            
            # Log the request without the key
            logger.info(f"Sending request to: {url.split('?')[0]}")
            
            headers = {"Content-Type": "application/json"}
            
            # Make the API call with proper timeout
            request_time = time.time()
            response = self.session.post(url, headers=headers, json=payload, timeout=30)
            response_time = time.time() - request_time
            
            logger.info(f"Gemini API responded in {response_time:.2f}s with status: {response.status_code}")
            
            # Process successful response
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                text = ""
                
                if 'candidates' in result and result['candidates'] and 'content' in result['candidates'][0]:
                    content = result['candidates'][0]['content']
                    if 'parts' in content:
                        for part in content['parts']:
                            if 'text' in part:
                                text += part['text']
                
                # Ensure response identifies as Gemini
                if "gemini" not in text.lower() and "google" not in text.lower():
                    text = "I am Gemini, Google's AI assistant.\n\n" + text
                
                logger.info(f"✅ Gemini response generated ({len(text)} chars)")
                return text
            else:
                logger.error(f"❌ Gemini API request failed: {response.status_code}")
                try:
                    error_info = response.json()
                    logger.error(f"Error details: {json.dumps(error_info)[:300]}")
                    
                    # Try with fallback model if appropriate
                    if "NOT_FOUND" in str(error_info) or "INVALID_ARGUMENT" in str(error_info):
                        return self._generate_with_fallback(user_message)
                except:
                    logger.error(f"Raw response: {response.text[:200]}")
                
                return "I'm Gemini, but I encountered an API issue. Let me try a different approach..." + self._generate_with_fallback(user_message)
        
        except Exception as e:
            logger.error(f"Error in Gemini service: {str(e)}")
            logger.error(traceback.format_exc())
            return "I'm Gemini, but I encountered an unexpected error. " + get_rule_based_response(conversation_history[-1]['content'] if conversation_history else "Help me")
    
    def _generate_with_fallback(self, user_message):
        """Generate a response using fallback models"""
        # List of fallback models to try in order
        fallback_models = [
            "gemini-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
        
        # Skip the current model if it's in the fallback list
        fallback_models = [m for m in fallback_models if m != self.model]
        
        # Try each fallback model
        for model in fallback_models:
            try:
                logger.info(f"Trying fallback model: {model}")
                
                url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{model}:generateContent?key={self.api_key}"
                
                # Simplified payload for fallback
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": f"{user_message}\n\nPlease respond as Gemini AI."
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 500
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = self.session.post(url, headers=headers, json=payload, timeout=20)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract text from response
                    text = ""
                    if 'candidates' in result and result['candidates'] and 'content' in result['candidates'][0]:
                        for part in result['candidates'][0]['content']['parts']:
                            if 'text' in part:
                                text += part['text']
                    
                    # Ensure response identifies as Gemini
                    if "gemini" not in text.lower() and "google" not in text.lower():
                        text = "I am Gemini, Google's AI assistant.\n\n" + text
                    
                    # Update the model for future requests
                    logger.info(f"✅ Fallback response generated with {model}")
                    self.model = model
                    
                    return text
            except Exception as e:
                logger.warning(f"Fallback attempt with {model} failed: {str(e)}")
                continue
        
        # If all fallbacks fail, use rule-based response
        logger.error("All fallback attempts failed, using rule-based response")
        return get_rule_based_response(user_message)
    
    def analyze_image(self, image_data, prompt="Analyze this image in detail"):
        """Analyze image using Google Gemini Vision API with robust fallbacks"""
        try:
            logger.info("Attempting Gemini image analysis")
            
            # Make sure we have valid image data
            if not image_data:
                return "I cannot analyze an empty image."
                
            # Convert to base64 if it isn't already
            if isinstance(image_data, bytes):
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            else:
                image_base64 = image_data
                
            # Find a working model - these are the current models that support vision
            models_to_try = [
                "gemini-1.5-pro",  # This is the latest model that supports image inputs
                "gemini-pro-vision",
                "gemini-1.0-pro-vision",
            ]
            
            logger.info(f"Will try these models: {', '.join(models_to_try)}")
            
            for model in models_to_try:
                try:
                    logger.info(f"Attempting image analysis with {model}")
                    
                    # Build URL with the model
                    url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{model}:generateContent?key={self.api_key}"
                    
                    # Build payload in the correct format for each model version
                    if "1.5" in model:
                        # Format for newer 1.5 models
                        payload = {
                            "contents": [{
                                "parts": [
                                    {"text": prompt},
                                    {
                                        "inline_data": {
                                            "mime_type": "image/jpeg",
                                            "data": image_base64
                                        }
                                    }
                                ]
                            }],
                            "generationConfig": {
                                "temperature": 0.3,
                                "topK": 32,
                                "topP": 1,
                                "maxOutputTokens": 1024
                            }
                        }
                    else:
                        # Format for older models
                        payload = {
                            "contents": [{
                                "parts": [
                                    {"text": prompt},
                                    {
                                        "inline_data": {
                                            "mime_type": "image/jpeg",
                                            "data": image_base64
                                        }
                                    }
                                ]
                            }],
                            "generationConfig": {
                                "temperature": 0.4,
                                "maxOutputTokens": 800
                            }
                        }
                    
                    headers = {"Content-Type": "application/json"}
                    
                    logger.info(f"Sending request to {model}")
                    
                    # Make the API call with extended timeout
                    response = self.session.post(url, headers=headers, json=payload, timeout=45)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Extract text from response
                        if 'candidates' in result and result['candidates']:
                            candidate = result['candidates'][0]
                            if 'content' in candidate and 'parts' in candidate['content']:
                                parts = candidate['content']['parts']
                                text = ""
                                for part in parts:
                                    if 'text' in part:
                                        text += part['text']
                                
                                if text:
                                    # Ensure response identifies as Gemini
                                    if "gemini" not in text.lower() and "google" not in text.lower():
                                        text = f"As Gemini, I've analyzed this image:\n\n{text}"
                                    
                                    logger.info(f"✅ Successfully analyzed image with {model}")
                                    return text
                                else:
                                    logger.warning(f"Empty text response from {model}")
                            else:
                                logger.warning(f"Unexpected response format from {model}: {candidate}")
                        else:
                            logger.warning(f"No candidates in response from {model}")
                    else:
                        logger.warning(f"{model} returned status {response.status_code}")
                        try:
                            error_json = response.json()
                            logger.warning(f"Error details: {json.dumps(error_json)}")
                        except:
                            logger.warning(f"Raw error response: {response.text[:200]}")
                
                except Exception as e:
                    logger.error(f"Error with {model}: {str(e)}")
            
            # Special handling for role-based payload format (alternative format)
            try:
                logger.info("Trying alternative payload format for Gemini Vision")
                
                # Use gemini-1.5-pro as it's more likely to work with role-based format
                model = "gemini-1.5-pro"
                url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{model}:generateContent?key={self.api_key}"
                
                # Role-based format (works with some API versions)
                alt_payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": "Please analyze this image in detail and describe what you see."
                                }, 
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1024
                    }
                }
                
                response = self.session.post(
                    url, 
                    headers={"Content-Type": "application/json"}, 
                    json=alt_payload, 
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        text = ""
                        for part in result['candidates'][0]['content']['parts']:
                            if 'text' in part:
                                text += part['text']
                        
                        if text:
                            if "gemini" not in text.lower() and "google" not in text.lower():
                                text = "As Gemini, I've analyzed this image:\n\n" + text
                            logger.info("✅ Gemini image analysis successful with alternative payload")
                            return text
                else:
                    logger.warning(f"Alternative payload attempt failed with status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Alternative payload approach failed: {str(e)}")
            
            # If all attempts fail, return a helpful message
            logger.error("All Gemini vision models failed to analyze the image")
            return "As Gemini, I can see you've shared an image, but I'm having technical difficulties analyzing it in detail. The image analysis service is currently experiencing issues. I can still help with text-based questions though!"
                
        except Exception as e:
            logger.error(f"Gemini image analysis error: {str(e)}")
            logger.error(traceback.format_exc())
            return "As Gemini, I can see this is an image, but I couldn't analyze it in detail due to a technical issue. Our image analysis service is having temporary problems."
