import asyncio
import logging
import os
from datetime import datetime, timezone
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Configuration from environment variables (for Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8299834283:AAED5dLGBUoUZ4GRf0LP-8F8-HqwSJ1rPqA")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@BtcRadars")

# Using multiple APIs for reliability
PRICE_APIS = [
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "https://api.coinbase.com/v2/prices/BTC-USD/spot",
]

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BitcoinPriceBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.last_price = None
        self.session = None
        
    async def get_bitcoin_price(self):
        """Fetch current Bitcoin price from multiple APIs"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Try CoinGecko first
        try:
            async with self.session.get(PRICE_APIS[0], timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['bitcoin']['usd'])
                    return round(price, 2)
        except Exception as e:
            logger.warning(f"CoinGecko API failed: {e}")
        
        # Fallback to Coinbase
        try:
            async with self.session.get(PRICE_APIS[1], timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['data']['amount'])
                    return round(price, 2)
        except Exception as e:
            logger.error(f"All APIs failed: {e}")
        
        return None
    
    def format_price(self, price):
        """Format price with comma separator and bold text"""
        formatted = f"${price:,.0f}"
        return f"<b>{formatted}</b>"
    
    async def send_price_update(self, price):
        """Send price update to channel"""
        try:
            message = self.format_price(price)
            await self.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=message,
                parse_mode=ParseMode.HTML
            )
            now = datetime.now(timezone.utc)
            logger.info(f"✅ Sent at {now.strftime('%H:%M:%S')} UTC: ${price:,.0f}")
            return True
        except TelegramError as e:
            logger.error(f"❌ Error: {e}")
            return False
    
    async def wait_until_next_30_second_mark(self):
        """Wait until the next :00 or :30 second mark in UTC"""
        while True:
            now = datetime.now(timezone.utc)
            current_second = now.second
            current_microsecond = now.microsecond
            
            # Calculate seconds to wait until next :00 or :30
            if current_second < 30:
                target_second = 30
            else:
                target_second = 60
            
            wait_seconds = target_second - current_second - (current_microsecond / 1_000_000)
            
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
                break
            else:
                # If we're already past the mark, wait a tiny bit and recalculate
                await asyncio.sleep(0.1)
    
    async def run(self):
        """Main bot loop"""
        logger.info("🚀 Bitcoin Price Bot started!")
        logger.info(f"📢 Channel: {CHANNEL_USERNAME}")
        logger.info(f"⏱️  Posts at :00 and :30 seconds (UTC)")
        
        try:
            while True:
                try:
                    # Wait until next :00 or :30 second mark
                    await self.wait_until_next_30_second_mark()
                    
                    # Get current price
                    current_price = await self.get_bitcoin_price()
                    
                    if current_price is not None:
                        # Check if price has changed
                        if self.last_price is None or current_price != self.last_price:
                            # Send update
                            success = await self.send_price_update(current_price)
                            if success:
                                self.last_price = current_price
                        else:
                            now = datetime.now(timezone.utc)
                            logger.info(f"⏭️  {now.strftime('%H:%M:%S')} UTC - Unchanged: ${current_price:,.0f}")
                    else:
                        logger.warning("⚠️  Could not fetch price")
                    
                except Exception as e:
                    logger.error(f"Error: {e}")
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Stopped")
        finally:
            if self.session:
                await self.session.close()
            logger.info("👋 Shutdown complete")

async def main():
    """Entry point"""
    bot = BitcoinPriceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
