import base64
import logging
import traceback
from PIL import Image
from io import BytesIO
import requests
import re

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Dedicated image analysis service for direct integration with Gemini"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.api_version = "v1beta"
        
    def is_valid_base64(self, s):
        """Check if the string is valid base64 encoding"""
        try:
            # Try to decode it to verify it's valid base64
            if len(s) % 4 != 0:  # Valid base64 should be divisible by 4
                return False
                
            # Check if it contains valid base64 characters
            if not re.match('^[A-Za-z0-9+/]+[=]{0,2}$', s):
                return False
                
            return True
        except Exception:
            return False
            
    def extract_base64_from_data_url(self, data_url):
        """Extract the base64 component from a data URL"""
        if not data_url or not isinstance(data_url, str):
            return None
            
        # Match common data URL pattern
        match = re.match(r'data:image/([a-zA-Z]+);base64,([^"]+)', data_url)
        if match:
            return match.group(2)
        return None
    
    def analyze_image(self, image_data):
        """
        Analyze image using Gemini Vision API
        
        Args:
            image_data: Can be raw bytes, base64 string, or data URL
        """
        try:
            # Handle different image input formats
            base64_string = None
            
            # Case 1: It's a data URL (data:image/jpeg;base64,...)
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                logger.info("Received image as data URL")
                base64_string = self.extract_base64_from_data_url(image_data)
                if not base64_string:
                    raise ValueError("Invalid data URL format")
                    
            # Case 2: It's already a base64 string
            elif isinstance(image_data, str) and self.is_valid_base64(image_data):
                logger.info("Received image as base64 string")
                base64_string = image_data
                
            # Case 3: It's binary image data
            elif not isinstance(image_data, str):
                logger.info("Received image as binary data, converting to base64")
                try:
                    # Validate and optimize the image
                    img = Image.open(BytesIO(image_data))
                    # Convert to RGB if needed (removing alpha channel that can cause issues)
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                        
                    # Optimize for API
                    if max(img.size) > 1600:  # Resize very large images
                        img.thumbnail((1600, 1600), Image.LANCZOS)
                        
                    # Save as JPEG to BytesIO
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG", quality=90)
                    img_bytes = buffered.getvalue()
                    base64_string = base64.b64encode(img_bytes).decode('utf-8')
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    # Try direct encoding if image processing fails
                    base64_string = base64.b64encode(image_data).decode('utf-8')
            else:
                raise ValueError("Unsupported image data format")
                
            # Validate we have a base64 string now
            if not base64_string:
                raise ValueError("Could not convert image data to base64")
                
            # Now use the base64 string for Gemini Vision API
            return self._analyze_with_gemini(base64_string)
            
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            logger.error(traceback.format_exc())
            return f"As Gemini, I'm unable to analyze this image due to a technical issue: {str(e)[:100]}"
            
    def _analyze_with_gemini(self, base64_image):
        """Send the base64 image to Gemini Vision API"""
        models_to_try = ["gemini-pro-vision", "gemini-1.5-pro-vision"]
        
        detailed_prompt = """
        Please analyze this image comprehensively and describe:
        1. What's shown in the image (people, objects, scene)
        2. Any notable visual elements, colors, or composition
        3. Any text visible in the image
        4. The context or setting of the image
        
        Be specific and detailed in your description.
        Begin with "As Gemini, I can see that this image shows..."
        """
        
        for model in models_to_try:
            try:
                logger.info(f"Analyzing image with Gemini {model}")
                url = f"https://generativelanguage.googleapis.com/{self.api_version}/models/{model}:generateContent?key={self.api_key}"
                
                # Format payload according to Gemini API requirements
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": detailed_prompt.strip()},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1024,
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = self.session.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract text from response
                    if ('candidates' in result and 
                        result['candidates'] and 
                        'content' in result['candidates'][0]):
                        
                        text_parts = []
                        for part in result['candidates'][0]['content']['parts']:
                            if 'text' in part:
                                text_parts.append(part['text'])
                        
                        full_text = ''.join(text_parts)
                        
                        # If response is meaningful
                        if len(full_text) > 50:
                            logger.info(f"✓ Successfully analyzed image ({len(full_text)} chars)")
                            
                            # Ensure response identifies as Gemini
                            if not any(name in full_text.lower() for name in ["gemini", "google ai"]):
                                full_text = f"As Gemini, I can see that this image shows {full_text}"
                            
                            return full_text
                
                logger.warning(f"Model {model} failed with status {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"Error response: {response.text[:200]}...")
                
            except Exception as e:
                logger.error(f"Error with {model}: {str(e)}")
                continue
        
        # If all models fail
        return "As Gemini, I can see this is an image, but I'm currently unable to analyze its contents in detail. This could be due to the image format, content, or processing limitations."
