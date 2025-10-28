python
import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', "8325365323:AAFChUhPqukejAKYQ5QcFom6xYsPNwVYl2Q")
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', "@BtcRadars")
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 30))

last_price = None

async def get_bitcoin_price():
    apis = [
        {
            "name": "Blockchain.info",
            "url": "https://blockchain.info/ticker",
            "parser": lambda data: float(data['USD']['last'])
        },
        {
            "name": "CoinCap",
            "url": "https://api.coincap.io/v2/assets/bitcoin",
            "parser": lambda data: float(data['data']['priceUsd'])
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for api in apis:
            try:
                async with session.get(api['url'], timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = api['parser'](data)
                        logger.info(f"قیمت: ${price:,.0f}")
                        return round(price, 0)
            except Exception as e:
                logger.warning(f"خطا در {api['name']}: {e}")
                continue
    return None

def format_price(price):
    formatted = f"${price:,.0f}"
    return f"**{formatted}**"

async def send_price_to_channel(bot, price):
    try:
        message = format_price(price)
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"ارسال شد: {message}")
        return True
    except TelegramError as e:
        logger.error(f"خطا: {e}")
        return False

async def price_monitor():
    global last_price
    bot = Bot(token=BOT_TOKEN)
    logger.info("ربات شروع شد...")
    logger.info(f"کانال: {CHANNEL_USERNAME}")
    logger.info(f"فاصله چک: {CHECK_INTERVAL} ثانیه")
    
    while True:
        try:
            current_price = await get_bitcoin_price()
            
            if current_price is not None:
                if last_price is None or current_price != last_price:
                    success = await send_price_to_channel(bot, current_price)
                    if success:
                        last_price = current_price
            
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"خطا: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(price_monitor())
    except KeyboardInterrupt:
        logger.info("ربات متوقف شد.")
```
