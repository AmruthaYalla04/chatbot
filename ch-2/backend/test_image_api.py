import sys
import os
import base64
import json
import logging
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def optimize_image(image_path, max_size_mb=3):
    """Optimize image for the API (resize and compress)"""
    try:
        # Open and process the image
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            
        # Convert to PIL Image
        img = Image.open(BytesIO(img_data))
        
        # Print original size
        original_size = len(img_data) / (1024 * 1024)
        logger.info(f"Original image: {img.width}x{img.height}, {original_size:.2f} MB")
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large
        max_dimension = 1024
        if img.width > max_dimension or img.height > max_dimension:
            if img.width > img.height:
                new_width = max_dimension
                new_height = int(img.height * (max_dimension / img.width))
            else:
                new_height = max_dimension
                new_width = int(img.width * (max_dimension / img.height))
                
            logger.info(f"Resizing to {new_width}x{new_height}")
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Compress the image
        output = BytesIO()
        quality = 85
        img.save(output, format="JPEG", quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        # Calculate compression ratio
        compressed_size = len(compressed_data) / (1024 * 1024)
        logger.info(f"Compressed image: {img.width}x{img.height}, {compressed_size:.2f} MB")
        
        # Further compress if still too large
        while compressed_size > max_size_mb and quality > 30:
            quality -= 10
            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            compressed_data = output.getvalue()
            compressed_size = len(compressed_data) / (1024 * 1024)
            logger.info(f"Additional compression at quality={quality}: {compressed_size:.2f} MB")
        
        return base64.b64encode(compressed_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return None

def test_gemini_vision(image_path):
    """Test Gemini Vision API directly"""
    try:
        logger.info(f"Testing image analysis with file: {image_path}")
        
        # Prepare the image
        image_base64 = optimize_image(image_path)
        if not image_base64:
            return False
            
        # Define models to try
        models_to_try = [
            "gemini-1.5-pro",  # Latest model
            "gemini-pro-vision",  # Standard vision model
            "gemini-1.0-pro-vision"  # Legacy model
        ]
        
        logger.info(f"Will try these models: {', '.join(models_to_try)}")
        
        for model in models_to_try:
            try:
                logger.info(f"\n\n--- Testing {model} ---")
                
                # Build URL for the model
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                
                # Prepare the payload
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Analyze this image in detail. Describe what you see."},
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
                        "maxOutputTokens": 800,
                        "topP": 1.0
                    }
                }
                
                logger.info(f"Sending request to {model}")
                
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                logger.info(f"{model} response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for candidates
                    if 'candidates' in result and result['candidates']:
                        text = ""
                        for part in result['candidates'][0]['content']['parts']:
                            if 'text' in part:
                                text += part['text']
                        
                        print(f"\n{'-' * 40}")
                        print(f"MODEL: {model} - SUCCESS")
                        print(f"{'-' * 40}")
                        print(text[:500] + "..." if len(text) > 500 else text)
                        print(f"{'-' * 40}\n")
                        
                        logger.info(f"Model {model} succeeded! Use this in your application.")
                        return True
                    else:
                        logger.warning(f"No candidates in {model} response")
                else:
                    logger.warning(f"{model} failed. Status: {response.status_code}")
                    try:
                        error_info = response.json()
                        logger.warning(f"Error: {json.dumps(error_info, indent=2)}")
                    except:
                        logger.warning(f"Raw error: {response.text[:200]}")
                        
            except Exception as e:
                logger.error(f"Error testing {model}: {str(e)}")
                
        logger.error("All models failed.")
        return False
                
    except Exception as e:
        logger.error(f"Error during image test: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_image_api.py <image_path>")
        sys.exit(1)
        
    test_gemini_vision(sys.argv[1])
