
import asyncio
from telegram import Bot
from config import TELEGRAM_TOKEN

async def reset():
    print("🔄 Resetting webhook...")
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook deleted! You can now use polling.")

if __name__ == "__main__":
    asyncio.run(reset())
