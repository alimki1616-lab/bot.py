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
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@BtcPrice3")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BitcoinPriceBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.last_sent_price = None
        self.session = None
        
    async def get_bitcoin_price(self):
        """Fetch Bitcoin price from Coinbase API (most reliable and fast)"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Coinbase API - fast and reliable
        try:
            async with self.session.get(
                "https://api.coinbase.com/v2/prices/BTC-USD/spot",
                timeout=8
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['data']['amount'])
                    # Round to integer to avoid decimal differences
                    return int(round(price))
                else:
                    logger.error(f"Coinbase API returned status: {response.status}")
        except Exception as e:
            logger.error(f"Coinbase API failed: {e}")
        
        # Fallback to CoinGecko
        try:
            async with self.session.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=8
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['bitcoin']['usd'])
                    return int(round(price))
                else:
                    logger.error(f"CoinGecko API returned status: {response.status}")
        except Exception as e:
            logger.error(f"CoinGecko API failed: {e}")
        
        return None
    
    def format_price(self, price):
        """Format price with comma separator and bold text"""
        formatted = f"${price:,}"
        return f"<b>{formatted}</b>"
    
    async def send_price_update(self, price):
        """Send price update to channel"""
        try:
            # Double check: Don't send if same as last sent price
            if self.last_sent_price == price:
                logger.warning(f"🚫 Prevented duplicate send: ${price:,}")
                return False
            
            message = self.format_price(price)
            await self.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=message,
                parse_mode=ParseMode.HTML
            )
            
            # Update last sent price
            self.last_sent_price = price
            now = datetime.now(timezone.utc)
            logger.info(f"✅ SENT at {now.strftime('%H:%M:%S')} UTC → ${price:,}")
            return True
        except TelegramError as e:
            logger.error(f"❌ Telegram Error: {e}")
            return False
    
    async def run(self):
        """Main bot loop - synced with UTC clock"""
        logger.info("🚀 Bitcoin Price Bot Started!")
        logger.info(f"📢 Channel: {CHANNEL_USERNAME}")
        logger.info(f"⏱️  Posting every 30 seconds at :00 and :30 (UTC)")
        logger.info(f"🌐 Using Coinbase API (primary) + CoinGecko (backup)")
        
        try:
            while True:
                # Get current UTC time
                now = datetime.now(timezone.utc)
                current_second = now.second
                current_microsecond = now.microsecond
                
                # Calculate seconds until next :00 or :30 mark
                if current_second < 30:
                    target = 30
                    wait = 30 - current_second - (current_microsecond / 1_000_000)
                else:
                    target = 60
                    wait = 60 - current_second - (current_microsecond / 1_000_000)
                
                logger.info(f"⏳ Waiting {wait:.1f}s until :{target:02d}...")
                
                if wait > 0:
                    await asyncio.sleep(wait)
                
                # Verify timing
                now_check = datetime.now(timezone.utc)
                logger.info(f"🕐 Woke at {now_check.strftime('%H:%M:%S')} UTC")
                
                # Fetch and send price
                try:
                    current_price = await self.get_bitcoin_price()
                    
                    if current_price is not None:
                        logger.info(f"💰 Fetched: ${current_price:,}")
                        
                        # Check if price changed from last SENT price
                        if self.last_sent_price != current_price:
                            logger.info(f"📊 Changed: ${self.last_sent_price or 0:,} → ${current_price:,}")
                            await self.send_price_update(current_price)
                        else:
                            logger.info(f"⏭️  Unchanged: ${current_price:,} - SKIP")
                    else:
                        logger.warning("⚠️  Failed to fetch price")
                        
                except Exception as e:
                    logger.error(f"❌ Error: {e}")
                
                # Sleep to prevent immediate re-execution
                await asyncio.sleep(1)
                logger.info("─" * 50)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Bot Stopped")
        finally:
            if self.session:
                await self.session.close()
            logger.info("👋 Shutdown Complete")

async def main():
    """Entry point"""
    bot = BitcoinPriceBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
