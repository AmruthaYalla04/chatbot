import requests
import base64
import logging
import json
import sys
import os
from PIL import Image
from io import BytesIO

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectGeminiImageAnalyzer:
    """Direct implementation of Gemini's Vision API for troubleshooting"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        
    def compress_image(self, image_data, quality=85, max_size=4 * 1024 * 1024):
        """Compress image to ensure it fits within API limits"""
        try:
            # Open image
            img = Image.open(BytesIO(image_data))
            
            # Convert to RGB if it has alpha channel
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize if image is too large
            max_dimension = 1024
            width, height = img.size
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
                
            # Save to BytesIO with compression
            output = BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            compressed_data = output.getvalue()
            
            # If still too large, further reduce quality
            if len(compressed_data) > max_size and quality > 40:
                return self.compress_image(image_data, quality=quality-10, max_size=max_size)
                
            logger.info(f"Compressed image from {len(image_data)/1024:.1f}KB to {len(compressed_data)/1024:.1f}KB")
            return compressed_data
            
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return image_data  # Return original if compression fails
    
    def analyze_image(self, image_path=None, image_data=None):
        """
        Analyze an image using Gemini Vision API
        Args:
            image_path: Path to image file
            image_data: Raw image data (bytes)
        """
        try:
            # Load image data from file if path is provided
            if image_path and not image_data:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
            
            if not image_data:
                raise ValueError("No image data provided")
                
            # Compress image to ensure it's under API limits
            image_data = self.compress_image(image_data)
                
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Create request payload
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={self.api_key}"
            
            # Make the request with the exact format from Google's documentation
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Describe this image in detail. Include what you see - people, objects, activities, background, colors, etc. Be specific but concise."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "topP": 1.0,
                    "topK": 32,
                    "maxOutputTokens": 800,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Log request info
            logger.info(f"Sending request to Gemini API: {url.split('?')[0]}")
            logger.info(f"Image base64 length: {len(base64_image)}")
            
            # Make the request
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            # Process successful response
            if response.status_code == 200:
                result = response.json()
                
                # Debug: Log full response structure
                logger.info(f"Response structure: {json.dumps(result, indent=2)[:500]}...")
                
                # Extract text from response
                text = ""
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'text' in part:
                                text += part['text']
                
                if text:
                    logger.info(f"Successfully extracted text ({len(text)} chars)")
                    logger.info(f"First 100 chars: {text[:100]}...")
                    return text
                else:
                    logger.error("Response contained no text output")
                    return "Failed to analyze the image: no text in response"
            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response body: {response.text}")
                
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    return f"Error analyzing image: {error_message}"
                except:
                    return f"Error analyzing image: Status code {response.status_code}"
                    
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return f"Error: {str(e)}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET")
# Test function
def test_image_analysis(image_path):
    """Test the analyzer with a specific image"""
    # Use API key from environment or default 
    api_key = os.environ.get("GEMINI_API_KEY")
    analyzer = DirectGeminiImageAnalyzer(api_key)
    
    result = analyzer.analyze_image(image_path=image_path)
    print("\n===== ANALYSIS RESULT =====")
    print(result)
    print("===========================")
    
    # Save result to file
    with open("analysis_result.txt", "w") as f:
        f.write(result)
    
    print(f"Result also saved to analysis_result.txt")
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_image_analysis(image_path)
    else:
        print("Please provide an image path as argument")
        print("Example: python fix_image_analysis.py path/to/image.jpg")
