import logging
import base64
import io
import requests
import json
import os
from PIL import Image
import base64
from io import BytesIO
import numpy as np
import traceback

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Handles image analysis using multiple methods with fallbacks"""
    
    def __init__(self, openai_service=None, gemini_service=None, vision_api_key=None):
        self.openai_service = openai_service
        self.gemini_service = gemini_service
        self.vision_api_key = vision_api_key or os.environ.get("GOOGLE_VISION_API_KEY")
        
    async def analyze_image(self, image_data, preferred_model="gemini"):
        """
        Analyze image using available services with fallbacks
        Returns a standardized analysis result
        """
        try:
            # Validate image data
            if not image_data:
                logger.error("Empty image data received")
                return "", {"error": "No image data provided"}
                
            # Convert to PIL Image to validate and get basic info
            try:
                image = Image.open(BytesIO(image_data))
                width, height = image.size
                format_name = image.format
            except Exception as e:
                logger.error(f"Invalid image format: {str(e)}")
                return "", {"error": "Invalid image format", "description": str(e)}
            
            # Get base64 encoding for APIs
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Default analysis structure
            analysis = {
                "labels": [],
                "text": "",
                "objects": [],
                "faces": 0,
                "safe_search": {
                    "adult": "UNKNOWN", 
                    "violence": "UNKNOWN"
                },
                "description": "Image analysis unavailable"
            }
            
            # Log which model is preferred
            logger.info(f"Analyzing image with preferred model: {preferred_model}")
            
            # Set success flag
            successful = False
            
            # Try the preferred model first
            if preferred_model == "gemini" and self.gemini_service:
                try:
                    logger.info("Using Gemini for image analysis")
                    description = self.gemini_service.analyze_image(image_base64)
                    if description and not description.startswith("As Gemini, I couldn't analyze"):
                        analysis["description"] = description
                        analysis["labels"] = self._extract_labels_from_description(description)
                        successful = True
                        logger.info("Gemini image analysis successful")
                    else:
                        logger.warning("Gemini returned error response")
                        # Don't mark as successful to try other services
                except Exception as e:
                    logger.warning(f"Gemini image analysis failed: {str(e)}")
            elif preferred_model == "openai" and self.openai_service:
                try:
                    logger.info("Using OpenAI for image analysis")
                    description = self.openai_service.analyze_image(image_base64)
                    analysis["description"] = description
                    analysis["labels"] = self._extract_labels_from_description(description)
                    successful = True
                    logger.info("OpenAI image analysis successful")
                except Exception as e:
                    logger.warning(f"OpenAI image analysis failed: {str(e)}")
            
            # Try other services if the preferred one failed
            if not successful and self.vision_api_key:
                try:
                    logger.info("Trying Google Vision API")
                    vision_analysis = await self._analyze_with_vision_api(image_base64)
                    if vision_analysis:
                        analysis.update(vision_analysis)
                        analysis["description"] = self._generate_description(analysis)
                        successful = True
                        logger.info("Google Vision API analysis successful")
                except Exception as e:
                    logger.warning(f"Google Vision API failed: {str(e)}")
            
            # Try remaining services as fallback
            if not successful:
                if preferred_model != "openai" and self.openai_service:
                    try:
                        logger.info("Trying OpenAI as fallback")
                        description = self.openai_service.analyze_image(image_base64)
                        analysis["description"] = description
                        analysis["labels"] = self._extract_labels_from_description(description)
                        successful = True
                        logger.info("OpenAI fallback successful")
                    except Exception as e:
                        logger.warning(f"OpenAI fallback failed: {str(e)}")
                
                if not successful and preferred_model != "gemini" and self.gemini_service:
                    try:
                        logger.info("Trying Gemini as fallback")
                        description = self.gemini_service.analyze_image(image_base64)
                        if description and not description.startswith("As Gemini, I couldn't analyze"):
                            analysis["description"] = description
                            analysis["labels"] = self._extract_labels_from_description(description)
                            successful = True
                            logger.info("Gemini fallback successful")
                    except Exception as e:
                        logger.warning(f"Gemini fallback failed: {str(e)}")
            
            # Basic fallback if everything else fails
            if not successful:
                logger.warning("All image analysis methods failed, using basic fallback")
                analysis["description"] = f"An image of format {format_name}, dimensions {width}x{height}. I couldn't analyze it in detail."
                analysis["labels"] = ["image"]
                
                # Add details about the format as detection
                if format_name:
                    analysis["labels"].append(format_name.lower())
            
            return image_base64, analysis
            
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            logger.error(traceback.format_exc())
            return "", {"error": "Failed to analyze image", "description": str(e)}
    
    async def _analyze_with_vision_api(self, image_base64):
        """Direct HTTP request to Vision API without using client library"""
        if not self.vision_api_key:
            return None
            
        url = f"https://vision.googleapis.com/v1/images:annotate?key={self.vision_api_key}"
        
        payload = {
            "requests": [
                {
                    "image": {
                        "content": image_base64
                    },
                    "features": [
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "TEXT_DETECTION"},
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 10},
                        {"type": "FACE_DETECTION", "maxResults": 10},
                        {"type": "SAFE_SEARCH_DETECTION"}
                    ]
                }
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'responses' in result and result['responses']:
                resp = result['responses'][0]
                
                analysis = {
                    "labels": [label['description'] for label in resp.get('labelAnnotations', [])],
                    "text": resp.get('fullTextAnnotation', {}).get('text', ''),
                    "objects": [obj['name'] for obj in resp.get('localizedObjectAnnotations', [])],
                    "faces": len(resp.get('faceAnnotations', [])),
                    "safe_search": {
                        "adult": resp.get('safeSearchAnnotation', {}).get('adult', 'UNKNOWN'),
                        "violence": resp.get('safeSearchAnnotation', {}).get('violence', 'UNKNOWN')
                    }
                }
                return analysis
                
        except Exception as e:
            logger.error(f"Vision API direct call failed: {str(e)}")
            return None
    
    def _generate_description(self, analysis):
        """Create a human-readable description from analysis data"""
        parts = []
        
        if analysis['labels']:
            parts.append(f"This appears to be {', '.join(analysis['labels'][:3])}")
        
        if analysis['objects']:
            parts.append(f"I can see {', '.join(analysis['objects'][:3])}")
        
        if analysis['faces'] > 0:
            parts.append(f"There {'is' if analysis['faces'] == 1 else 'are'} {analysis['faces']} {'person' if analysis['faces'] == 1 else 'people'}")
        
        if analysis['text']:
            text_preview = analysis['text'][:100] + '...' if len(analysis['text']) > 100 else analysis['text']
            parts.append(f"The image contains text: \"{text_preview}\"")
        
        if not parts:
            return "I can't determine what's in this image."
        
        return " ".join(parts)
    
    def _extract_labels_from_description(self, description):
        """Extract potential labels from AI-generated description"""
        # Simple heuristic - split by common separators and take words
        words = description.replace('.', ' ').replace(',', ' ').split()
        # Filter out common words, keep only nouns and adjectives
        common_words = {'the', 'a', 'an', 'and', 'is', 'are', 'in', 'on', 'of', 'with', 'this', 'that', 'it'}
        potential_labels = [w for w in words if len(w) > 3 and w.lower() not in common_words]
        
        # Deduplicate and return top 5
        return list(dict.fromkeys([w.lower() for w in potential_labels]))[:5]
