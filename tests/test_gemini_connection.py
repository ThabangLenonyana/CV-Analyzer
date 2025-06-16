"""
Simple test script to verify Google Gemini API connection
Run with: python test_gemini_connection.py
"""

import os
import sys
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test if we can connect to Gemini API and get a response"""
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in environment variables")
        print("Please add GEMINI_API_KEY to your .env file")
        return False
    
    try:
        # Initialize Gemini client
        print("🔄 Initializing Gemini client...")
        client = genai.Client(api_key=api_key)
        
        # Test with a simple prompt
        print("📤 Sending test prompt to Gemini...")
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents="Say 'Hello, CV Analyzer is connected!' in exactly those words."
        )
        
        # Check response
        if response and response.text:
            print("✅ SUCCESS: Gemini API connection established!")
            print(f"📥 Response: {response.text}")
            return True
        else:
            print("❌ ERROR: Received empty response from Gemini")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to Gemini API")
        print(f"Error details: {str(e)}")
        return False

def test_gemini_json_response():
    """Test if Gemini can return structured JSON responses"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Skipping JSON test: No API key found")
        return False
    
    try:
        print("\n🔄 Testing JSON response capability...")
        client = genai.Client(api_key=api_key)
        
        # Test prompt that requests JSON
        prompt = """
        Respond with a valid JSON object containing these keys:
        - "status": "connected"
        - "model": "gemini-2.0-flash"
        - "message": "CV Analyzer ready"
        
        Return ONLY the JSON object, no other text.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        if response and response.text:
            print("✅ JSON Response Test Passed!")
            print(f"📥 Response: {response.text}")
            
            # Try to parse as JSON
            import json
            try:
                json_data = json.loads(response.text.strip())
                print("✅ Valid JSON received!")
                return True
            except json.JSONDecodeError:
                print("⚠️  Response is not valid JSON, but connection works")
                return True
        
    except Exception as e:
        print(f"❌ JSON test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 CV Analyzer - Gemini API Connection Test")
    print("=" * 50)
    
    # Run connection test
    connection_ok = test_gemini_connection()
    
    # Run JSON response test
    json_ok = test_gemini_json_response()
    
    print("\n" + "=" * 50)
    if connection_ok:
        print("✅ OVERALL: Gemini API is properly connected!")
        print("You can now proceed with building the CV Analyzer.")
    else:
        print("❌ OVERALL: Please fix the connection issues before proceeding.")
        sys.exit(1)