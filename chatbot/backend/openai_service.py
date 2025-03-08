import logging
import time
import os
import traceback
from alternatives import get_rule_based_response
import openai
from config import OPENAI_API_KEY

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIService:
    """Service class to handle OpenAI API interactions with fallbacks"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or OPENAI_API_KEY
        openai.api_key = self.api_key
        self.model = self._get_best_model()
        logger.info(f"OpenAI service initialized with model: {self.model}")
        
        # Try to import OpenAI library
        try:
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.openai = openai
            self.client = None
            
            # Try to import modern client
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI modern client available")
            except ImportError:
                logger.info("Using legacy OpenAI client")
                
            # Test the connection
            self._test_connection()
            
        except ImportError:
            logger.error("OpenAI library not installed")
            self.openai = None
    
    def _get_best_model(self):
        """Get the best working model from test file or default list"""
        # Try to read from our test file
        try:
            model_file = os.path.join(os.path.dirname(__file__), "working_openai_model.txt")
            if os.path.exists(model_file):
                with open(model_file, "r") as f:
                    model = f.read().strip()
                    if model:
                        return model
        except Exception:
            pass
            
        # Default to a reliable model
        return "gpt-4o-mini"
    
    def _test_connection(self):
        """Test the API connection silently"""
        if not self.api_key:
            logger.warning("No OpenAI API key provided - will use fallbacks")
            return False
            
        models_to_try = [self.model, "gpt-4o-mini", "gpt-3.5-turbo"]
        
        for model in models_to_try:
            try:
                logger.info(f"Testing OpenAI connection with model: {model}")
                
                if self.client:  # Modern client
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=1,
                        temperature=0.7
                    )
                    logger.info("✅ OpenAI API connection test successful (modern client)")
                    self.model = model  # Update to working model
                    return True
                else:  # Legacy client
                    response = self.openai.ChatCompletion.create(
                        model=model,
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=1,
                        temperature=0.7
                    )
                    logger.info("✅ OpenAI API connection test successful (legacy client)")
                    self.model = model  # Update to working model
                    return True
                    
            except Exception as e:
                logger.warning(f"OpenAI connection test failed with {model}: {str(e)}")
                continue
                
        logger.error("❌ All OpenAI models failed connection test")
        return False
        
    def generate_response(self, conversation_history):
        """Generate a response using OpenAI API with clear model identification"""
        # Check if OpenAI library is available
        if not self.openai:
            logger.error("OpenAI library not available")
            return get_rule_based_response(conversation_history[-1]['content'] if conversation_history else "Hello")
        
        # Log very clearly that we're using OpenAI
        logger.info("🤖 USING OPENAI MODEL FOR RESPONSE GENERATION")
        
        # Add system message to identify as OpenAI/ChatGPT
        formatted_messages = []
        formatted_messages.append({
            "role": "system", 
            "content": "You are ChatGPT, an AI assistant by OpenAI. Start your response by identifying yourself as 'I am ChatGPT, OpenAI's assistant.'"
        })
        
        # Add the user conversation history
        for msg in conversation_history:
            formatted_messages.append(msg)
            
        # Try with primary model first
        try:
            logger.debug(f"Trying OpenAI completion with {self.model}")
            
            # Add timestamp for logging
            request_time = time.time()
            
            if self.client:  # Modern client
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    max_tokens=800,
                    temperature=0.7
                )
                
                response_time = time.time() - request_time
                logger.info(f"OpenAI API responded in {response_time:.2f} seconds")
                
                response_text = response.choices[0].message.content.strip()
            else:  # Legacy client
                response = self.openai.ChatCompletion.create(
                    model=self.model,
                    messages=formatted_messages,
                    max_tokens=800,
                    temperature=0.7
                )
                
                response_time = time.time() - request_time
                logger.info(f"OpenAI API responded in {response_time:.2f} seconds")
                
                response_text = response["choices"][0]["message"]["content"].strip()
            
            # Force identification as ChatGPT if not present
            if "chatgpt" not in response_text.lower() and "openai" not in response_text.lower():
                response_text = "I am ChatGPT, OpenAI's assistant.\n\n" + response_text
                
            logger.info(f"✅ OpenAI response successful ({len(response_text)} chars)")
            return response_text
            
        except Exception as e:
            logger.warning(f"Failed with {self.model}: {str(e)}")
            
            # Try with fallback models
            return self._try_fallback_models(formatted_messages)
    
    def _try_fallback_models(self, formatted_messages):
        """Try fallback models if the primary one fails"""
        fallback_models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-3.5-turbo-instruct"]
        
        for model in fallback_models:
            if model == self.model:  # Skip if it's the already-failed model
                continue
                
            try:
                logger.debug(f"Trying fallback with model {model}")
                
                if self.client:  # Modern client
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=formatted_messages,
                        max_tokens=800,
                        temperature=0.7
                    )
                    response_text = response.choices[0].message.content.strip()
                else:  # Legacy client
                    response = self.openai.ChatCompletion.create(
                        model=model,
                        messages=formatted_messages,
                        max_tokens=800,
                        temperature=0.7
                    )
                    response_text = response["choices"][0]["message"]["content"].strip()
                
                # Force identification as ChatGPT if not present
                if "chatgpt" not in response_text.lower() and "openai" not in response_text.lower():
                    response_text = "I am ChatGPT, OpenAI's assistant.\n\n" + response_text
                
                logger.info(f"✅ OpenAI fallback successful with {model}")
                return response_text
                
            except Exception as e:
                logger.warning(f"Fallback failed with {model}: {str(e)}")
                continue
        
        # If all models failed, use rule-based response
        logger.error("All OpenAI models failed, using rule-based fallback")
        
        # Extract the last user message
        last_user_message = ""
        for msg in reversed(formatted_messages):
            if msg['role'] == 'user':
                last_user_message = msg['content'].strip()
                break
        
        # If we couldn't find a user message, use a default
        if not last_user_message:
            last_user_message = "Help me"
            
        fallback_response = "I am ChatGPT, but I'm having trouble connecting to my knowledge base. " + get_rule_based_response(last_user_message)
        return fallback_response

    def analyze_image(self, image_data, prompt="Analyze this image in detail"):
        """Analyze image using OpenAI's GPT-4 Vision API"""
        try:
            if not self.client:
                logger.warning("OpenAI client not available, trying legacy client")
                raise Exception("Modern client not available")
                
            # Try with modern client first
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Modern client image analysis failed: {str(e)}")
                raise e
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            return f"I apologize, but I couldn't analyze the image due to an error: {str(e)}"
