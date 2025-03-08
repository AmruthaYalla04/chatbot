import requests
import json
import base64
import sys
import os
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

def compress_image(image_data, quality=85, max_size=4 * 1024 * 1024):
    """Compress image to ensure it fits within API limits"""
    try:
        # Open image
        img = Image.open(BytesIO(image_data))
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Resize if too large
        max_dimension = 1024
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"Resized image from {width}x{height} to {new_width}x{new_height}")
                
        # Save to BytesIO with compression
        output = BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        # If still too large, further reduce quality
        if len(compressed_data) > max_size and quality > 40:
            return compress_image(image_data, quality=quality-10, max_size=max_size)
                
        print(f"Compressed image from {len(image_data)/1024:.1f}KB to {len(compressed_data)/1024:.1f}KB")
        return compressed_data
            
    except Exception as e:
        print(f"Image compression failed: {e}")
        return image_data  # Return original if compression fails

def fix_gemini_vision(image_path):
    """Test Gemini Vision API directly to diagnose issues"""
    try:
        print(f"Testing Gemini Vision with image: {image_path}")
        
        # Read and compress image
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        image_data = compress_image(image_data)
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Try with gemini-1.5-pro model first - this is the latest that supports images
        print("\nTrying with gemini-1.5-pro (latest model)...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        
        # Construct the payload based on current API docs
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Analyze this image in detail. Describe what you see."
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
                "temperature": 0.4,
                "maxOutputTokens": 800,
                "topP": 1,
                "topK": 32
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        print("Sending request to Gemini Vision API...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("\nGemini Vision response structure:")
                print(json.dumps(result, indent=2)[:1000] + "...")
                
                # Extract text from response
                if 'candidates' in result and result['candidates']:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    print("\nAnalysis result:")
                    print("=" * 50)
                    print(text)
                    print("=" * 50)
                    print("\nTest successful! Gemini-1.5-pro worked for vision!")
                    return True
                else:
                    print("No candidates in response")
            except Exception as e:
                print(f"Error parsing response: {e}")
                print(f"Raw response: {response.text[:1000]}")
        
        # If first attempt failed, try with Pro Vision model
        print("\nTrying with gemini-pro-vision...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print("\nAnalysis result:")
                print("=" * 50)
                print(text)
                print("=" * 50)
                print("\nTest successful! gemini-pro-vision works.")
                return True
                
        # Try one more time with role-based format        
        print("\nTrying with gemini-1.5-pro and role-based format...")
        
        role_payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "Please analyze this image in detail."
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
                "maxOutputTokens": 800,
                "topP": 1
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=role_payload, timeout=60)
        
        if response.status_code == 200:
            print("\nSuccess with role-based format!")
            result = response.json()
            if 'candidates' in result and result['candidates']:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print("\nAnalysis result:")
                print("=" * 50)
                print(text)
                print("=" * 50)
                print("\nTest successful! gemini-1.5-pro with role-based format works.")
                return True
                
        return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fix_gemini_vision(sys.argv[1])
    else:
        print("Please provide an image path as argument")
        print("Example: python fix_gemini_service.py /path/to/image.jpg")
