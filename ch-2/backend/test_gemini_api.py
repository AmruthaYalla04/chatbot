#!/usr/bin/env python3
"""
Test utility to find the right API configuration for Gemini
"""
import requests
import json
import logging
import time
import sys
from pprint import pprint

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')



def test_gemini_configurations():
    """Test multiple Gemini API configurations to find one that works"""
    print("\n=== GEMINI API CONFIGURATION TESTER ===\n")
    
    # Configurations to test
    configurations = [
        {"name": "v1 with models/ prefix", "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1 without prefix", "url": f"https://generativelanguage.googleapis.com/v1/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1beta with prefix", "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1beta without prefix", "url": f"https://generativelanguage.googleapis.com/v1beta/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1beta1 with prefix", "url": f"https://generativelanguage.googleapis.com/v1beta1/models/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1beta1 without prefix", "url": f"https://generativelanguage.googleapis.com/v1beta1/gemini-pro:generateContent?key={API_KEY}"},
        {"name": "v1 with gemini-1.5-pro", "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={API_KEY}"},
        {"name": "v1 with gemini-1.0-pro", "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-1.0-pro:generateContent?key={API_KEY}"},
    ]
    
    working_configurations = []
    
    session = requests.Session()
    
    print(f"Testing with API key: {API_KEY[:5]}...{API_KEY[-4:]}")
    print(f"Testing {len(configurations)} configurations...\n")
    
    for i, config in enumerate(configurations, 1):
        print(f"[{i}/{len(configurations)}] Testing: {config['name']}")
        print(f"URL: {config['url'].split('?')[0]}")
        
        try:
            payload = {
                "contents": [
                    {
                        "parts": [{"text": "Say hello and identify yourself as Gemini AI"}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 100
                }
            }
            
            headers = {"Content-Type": "application/json"}
            
            # Try this configuration
            start_time = time.time()
            response = session.post(config["url"], headers=headers, json=payload, timeout=10)
            elapsed = time.time() - start_time
            
            print(f"Response: {response.status_code}, Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Try to extract generated text
                text = None
                if 'candidates' in response_data and response_data['candidates']:
                    if 'content' in response_data['candidates'][0]:
                        for part in response_data['candidates'][0]['content']['parts']:
                            if 'text' in part:
                                text = part['text']
                                break
                
                if text:
                    print(f"Generated text: {text[:100]}...")
                    print("\n✅ SUCCESS! This configuration works.\n")
                    working_configurations.append({
                        **config,
                        "response_time": elapsed,
                        "sample": text[:50]
                    })
                else:
                    print(f"❌ Unable to extract text from response: {json.dumps(response_data)[:200]}\n")
            else:
                print(f"❌ Failed with status {response.status_code}")
                try:
                    print(f"Error: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Raw response: {response.text[:200]}\n")
        except Exception as e:
            print(f"❌ Error: {str(e)}\n")
    
    # Show summary of results
    print("\n=== SUMMARY ===")
    print(f"Tested {len(configurations)} configurations")
    print(f"Found {len(working_configurations)} working configurations")
    
    if working_configurations:
        print("\nWorking configurations:")
        for i, config in enumerate(working_configurations, 1):
            print(f"{i}. {config['name']} ({config['response_time']:.2f}s)")
            print(f"   URL: {config['url'].split('?')[0]}")
            print(f"   Sample: {config['sample']}...")
        
        # Store the best configuration
        best_config = min(working_configurations, key=lambda x: x['response_time'])
        print(f"\nBest configuration: {best_config['name']} ({best_config['response_time']:.2f}s)")
        
        # Update the gemini_service.py file with this information
        write_config_to_file(best_config)
    else:
        print("\n❌ No working configurations found!")
        print("Please check your API key and ensure you have access to the Gemini API.")

def write_config_to_file(config):
    """Write the best configuration to a file for later use"""
    try:
        # Extract API version and model from URL
        url = config["url"]
        url_parts = url.split("/")
        
        # First part is the API version (v1, v1beta, etc.)
        api_version = url_parts[3]
        
        # Extract model information
        model_part = url_parts[4]
        if model_part.startswith("models/"):
            model = model_part.replace("models/", "").split(":")[0]
            uses_models_prefix = True
        else:
            model = model_part.split(":")[0]
            uses_models_prefix = False
        
        # Write to a file
        with open("working_gemini_config.json", "w") as f:
            json.dump({
                "api_version": api_version,
                "model": model,
                "uses_models_prefix": uses_models_prefix,
                "full_url_template": config["url"].replace(API_KEY, "[API_KEY]"),
                "response_time": config["response_time"]
            }, f, indent=2)
        
        print(f"\nSaved working configuration to working_gemini_config.json")
    except Exception as e:
        print(f"Error writing configuration: {str(e)}")

if __name__ == "__main__":
    test_gemini_configurations()
