import os
import openai
import logging

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
def test_openai_api():
    """Test OpenAI API connectivity and response."""
    api_key = OPENAI_API_KEY
    # Set API key
    openai.api_key = api_key
    os.environ["OPENAI_API_KEY"] = api_key
    
    # Print OpenAI version
    print(f"OpenAI version: {openai.__version__}")
    
    try:
        print("Attempting API call...")
        
        # Try chat completion API with gpt-4o-mini
        try:
            conversation_history = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"}
            ]
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=conversation_history,
                max_tokens=50
            )
            print(f"Response with gpt-4o-mini: {response.choices[0].message['content'].strip()}")
        except Exception as e:
            print(f"Failed with gpt-4o-mini: {str(e)}")
            
            # Try with gpt-3.5-turbo
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history,
                    max_tokens=50
                )
                print(f"Response with gpt-3.5-turbo: {response.choices[0].message['content'].strip()}")
            except Exception as e:
                print(f"Failed with gpt-3.5-turbo: {str(e)}")
                
                # Try with another model
                try:
                    response = openai.ChatCompletion.create(
                        model="ada",
                        messages=conversation_history,
                        max_tokens=50
                    )
                    print(f"Response with ada model: {response.choices[0].message['content'].strip()}")
                except Exception as e:
                    print(f"Failed with ada model: {str(e)}")
        
    except Exception as e:
        print(f"API test failed with error: {str(e)}")
        
    print("API test completed")

if __name__ == "__main__":
    test_openai_api()
