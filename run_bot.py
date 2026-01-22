
import subprocess
import sys
import os

def main():
    print("="*50)
    print("🚀 Starting K-Voice Coach...")
    print("="*50)
    
    # Check if .env exists
    # Check if .env exists (Optional for local dev, not needed for Cloud if env vars set)
    if not os.path.exists(".env"):
        print("⚠️ Warning: .env file not found. Assuming environment variables are set manually.")
    #    print("Please rename .env.example to .env and add your keys.")
    #    return

    # Run the bot
    try:
        # Using sys.executable ensures we use the same python interpreter
        subprocess.run([sys.executable, "bot.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"\n❌ Error running bot: {e}")

if __name__ == "__main__":
    main()
