"""
Setup script to configure API keys and test connections
"""
import os
import requests
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load existing environment variables
load_dotenv()

def find_best_gemini_model(api_key):
    """Find the best working Gemini model for this API key"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        logger.info("Finding the best Gemini model...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            models = result.get('models', [])
            
            # Filter for likely working models
            candidates = []
            for model in models:
                name = model['name']
                # Prioritize stable models with flash (faster) capability
                if ('gemini-1.5-flash' in name or 'gemini-2.0-flash' in name) and 'exp' not in name:
                    candidates.append(name)
            
            if candidates:
                # Try the first few models to see which works
                for model_name in candidates[:3]:
                    logger.info(f"Testing model: {model_name}")
                    
                    test_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{
                            "role": "user",
                            "parts": [{"text": "Hello"}]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 50
                        }
                    }
                    headers = {"Content-Type": "application/json"}
                    
                    try:
                        test_response = requests.post(test_url, headers=headers, json=payload, timeout=10)
                        if test_response.status_code == 200:
                            logger.info(f"Found working model: {model_name}")
                            return model_name
                    except:
                        continue
            
            # If no candidates work, try gemini-1.5-flash as default
            return "gemini-1.5-flash"
        else:
            logger.error(f"Failed to list models: {response.status_code}")
    except Exception as e:
        logger.error(f"Error finding best model: {str(e)}")
    
    return "gemini-1.5-flash"  # Default fallback
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")
def update_env_file(gemini_api_key=None, openai_api_key=None):
    """Update the .env file with API keys"""
    gemini_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
    openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    
    # Test Gemini API key
    if gemini_key:
        model = find_best_gemini_model(gemini_key)
        logger.info(f"Using Gemini model: {model}")
        
        # Update the service file with the best model
        update_gemini_service_file(model)
    
    # Read existing .env file
    env_content = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_content[key] = value
    except FileNotFoundError:
        logger.info(".env file not found, creating new one")
    except Exception as e:
        logger.error(f"Error reading .env file: {str(e)}")
    
    # Update keys
    if gemini_key:
        env_content["GEMINI_API_KEY"] = gemini_key
    if openai_key:
        env_content["OPENAI_API_KEY"] = openai_key
    
    # Add default variables if missing
    if "ACCESS_TOKEN_EXPIRE_MINUTES" not in env_content:
        env_content["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    if "SECRET_KEY" not in env_content:
         
        env_content["SECRET_KEY"] = os.getenv("SECRET_KEY")
    
    # Write updated .env file
    try:
        with open(env_path, "w") as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        logger.info(".env file updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {str(e)}")
        return False

def update_gemini_service_file(model_name):
    """Update the gemini_service.py file with the best model"""
    file_path = os.path.join(os.path.dirname(__file__), "gemini_service.py")
    
    try:
        with open(file_path, "r") as f:
            content = f.read()
        
        # Replace the model line using regex
        import re
        updated_content = re.sub(
            r'self\.model = ".*?"',
            f'self.model = "{model_name}"',
            content
        )
        
        with open(file_path, "w") as f:
            f.write(updated_content)
        
        logger.info(f"Updated gemini_service.py with model: {model_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating gemini_service.py: {str(e)}")
        return False

def main():
    print("\n===== API Key Setup =====\n")
    
    # Ask for Gemini API key
    current_gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if current_gemini_key:
        print(f"Current Gemini API key: {current_gemini_key[:5]}...{current_gemini_key[-4:]}")
        change = input("Do you want to change the Gemini API key? (y/n): ").lower() == 'y'
    else:
        print("No Gemini API key found")
        change = True
        
    if change:
        gemini_key = input("Enter your Gemini API key: ").strip()
    else:
        gemini_key = current_gemini_key
        
    # Ask for OpenAI API key
    current_openai_key = os.environ.get("OPENAI_API_KEY", "")
    if current_openai_key:
        print(f"Current OpenAI API key: {current_openai_key[:5]}...{current_openai_key[-4:]}")
        change = input("Do you want to change the OpenAI API key? (y/n): ").lower() == 'y'
    else:
        print("No OpenAI API key found")
        change = True
        
    if change:
        openai_key = input("Enter your OpenAI API key: ").strip()
    else:
        openai_key = current_openai_key
        
    # Update .env file
    updated = update_env_file(gemini_key, openai_key)
    
    if updated:
        print("\nAPI keys updated successfully!")
        print("Try running test_gemini.py to verify the Gemini connection")
    else:
        print("\nFailed to update API keys. Please check the error logs.")

if __name__ == "__main__":
    main()
