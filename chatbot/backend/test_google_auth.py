"""
Script to test Google OAuth configuration
Run this to verify your Google Client ID and other settings
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_google_config():
    print("\n=== Google OAuth Configuration Test ===\n")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id:
        print("❌ GOOGLE_CLIENT_ID is not set in your environment variables")
    else:
        print(f"✅ GOOGLE_CLIENT_ID is set: {client_id[:10]}...{client_id[-5:]}")
    
    if not client_secret:
        print("❌ GOOGLE_CLIENT_SECRET is not set in your environment variables")
    else:
        print(f"✅ GOOGLE_CLIENT_SECRET is set (hidden for security)")
    
    # Check if the Client ID matches the one in the frontend
    frontend_client_id = "748513885856-a8upflc11lkknnnqrrscdcnhije274cr.apps.googleusercontent.com"
    if client_id != frontend_client_id:
        print(f"⚠️  WARNING: Client ID in backend doesn't match frontend hardcoded value")
        print(f"   Backend: {client_id}")
        print(f"   Frontend: {frontend_client_id}")
    else:
        print("✅ Client IDs match between frontend and backend")
    
    print("\nFor successful Google OAuth:")
    print("1. Make sure your Google Cloud project has OAuth consent screen configured")
    print("2. Ensure you have added 'http://localhost:3000' as an authorized JavaScript origin")
    print("3. Verify that your Client ID and Secret are correct")
    
if __name__ == "__main__":
    test_google_config()
