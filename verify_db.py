import logging
import time
from services.db_service import DBService
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_DB")

def test_db():
    print("="*50)
    print("🗄 Testing Supabase Connection")
    print("="*50)
    
    try:
        db = DBService()
        
        # Test 1: Update User (Upsert)
        print("\n[1] Testing update_user (Upsert)...")
        start_time = time.time()
        # Use a dummy ID for testing
        db.update_user(123456789, "test_user", "Testy McTestFace")
        duration = time.time() - start_time
        print(f"✅ User upserted in {duration:.2f}s")
        
        # Test 2: Get Context (Read)
        print("\n[2] Testing get_context (Read)...")
        start_time = time.time()
        context = db.get_context(123456789)
        duration = time.time() - start_time
        print(f"✅ Context retrieved in {duration:.2f}s. Items: {len(context)}")
        
        print("\n🎉 Supabase is WORKING and FAST!")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db()
