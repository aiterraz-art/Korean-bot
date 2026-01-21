
import os
import sys
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Fix for Mac Silicon (Homebrew)
# Ensure pydub can find ffmpeg/ffprobe
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

def validate_env():
    """Validates that required environment variables are set."""
    required_vars = ["TELEGRAM_TOKEN", "GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.critical(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.critical("Please create a .env file with these variables.")
        sys.exit(1)
    
    logger.info("Environment variables validated successfully.")

# Expose variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Temporary storage for conversation history (state)
# In production, use a database (Redis/Postgres)
# Structure: {user_id: [{"role": "user", "parts": [...]}, ...]}
CONVERSATION_HISTORY = {}
