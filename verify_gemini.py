import asyncio
import os
import logging
from services.gemini_service import GeminiService
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_GEMINI")

async def test_gemini():
    print("="*50)
    print("🤖 Testing Gemini Service")
    print("="*50)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in env.")
        return

    print(f"🔑 API Key found: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        service = GeminiService()
        print(f"✅ Service initialized with model: {service.model.model_name}")
        
        # Test Simple Text
        print("\n[1] Sending Test Text Prompt...")
        test_input = "Hola, esto es una prueba de conectividad."
        response = await service.analyze_text(test_input)
        
        print("\n✅ Response Received:")
        print(response)
        
        if response.get("reply_text"):
            print("🎉 Gemini is WORKING!")
        else:
            print("⚠️ Gemini responded but structure seems wrong.")
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini())
