import os
import asyncio
import logging
from datetime import datetime, timezone
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تنظیمات از environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8299834283:AAED5dLGBUoUZ4GRf0LP-8F8-HqwSJ1rPqA')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@BtcRadars')
INTERVAL_SECONDS = int(os.getenv('INTERVAL_SECONDS', '30'))

class BitcoinPriceBot:
    def __init__(self, token: str, channel: str):
        self.bot = Bot(token=token)
        self.channel = channel
        self.session = None
        self.last_price = None
        
    async def get_bitcoin_price(self):
        """دریافت قیمت بیت کوین با fallback از چندین API"""
        
        # لیست APIهای مختلف برای fallback - بهترین‌ها اول
        apis = [
            {
                'name': 'Binance',
                'url': 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT',
                'parser': lambda data: float(data['price'])
            },
            {
                'name': 'CoinGecko',
                'url': 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                'parser': lambda data: data['bitcoin']['usd']
            },
            {
                'name': 'Kraken',
                'url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
                'parser': lambda data: float(data['result']['XXBTZUSD']['c'][0])
            },
            {
                'name': 'CoinDesk',
                'url': 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json',
                'parser': lambda data: data['bpi']['USD']['rate_float']
            }
        ]
        
        # تلاش با هر API
        for api in apis:
            try:
                async with self.session.get(api['url'], timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = api['parser'](data)
                        logger.info(f"قیمت از {api['name']} دریافت شد: ${price:,.2f}")
                        return price
                    else:
                        logger.warning(f"{api['name']} - خطا {response.status}")
            except Exception as e:
                logger.warning(f"{api['name']} - خطا: {e}")
                continue
        
        logger.error("تمام APIها شکست خوردند!")
        return None
    
    def format_price(self, price: float, timestamp: str) -> str:
        """فرمت کردن قیمت با کاما و bold"""
        formatted_price = f"${price:,.2f}"
        message = f"<b>{formatted_price}</b>\n\n🕐 {timestamp} UTC"
        return message
    
    async def send_price_to_channel(self):
        """ارسال قیمت به کانال فقط در صورت تغییر"""
        try:
            price = await self.get_bitcoin_price()
            if price:
                # چک کردن تغییر قیمت - فقط اگر تغییر کرده باشد ارسال می‌شود
                if self.last_price is None or abs(price - self.last_price) >= 0.01:
                    # گرفتن زمان UTC
                    utc_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    
                    message = self.format_price(price, utc_time)
                    await self.bot.send_message(
                        chat_id=self.channel,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    logger.info(f"قیمت ارسال شد: {price}")
                    self.last_price = price
                else:
                    logger.info(f"قیمت تغییر نکرده: {price}")
            else:
                logger.warning("قیمت دریافت نشد")
        except TelegramError as e:
            logger.error(f"خطا در ارسال پیام به تلگرام: {e}")
        except Exception as e:
            logger.error(f"خطای غیرمنتظره: {e}")
    
    async def start(self):
        """شروع بات و ارسال قیمت هر 30 ثانیه"""
        logger.info(f"بات شروع به کار کرد. ارسال قیمت به {self.channel} هر {INTERVAL_SECONDS} ثانیه")
        
        # ایجاد session برای درخواست‌های HTTP
        self.session = aiohttp.ClientSession()
        
        try:
            # تست اتصال با ارسال اولین پیام
            await self.send_price_to_channel()
            
            # حلقه اصلی
            while True:
                await asyncio.sleep(INTERVAL_SECONDS)
                await self.send_price_to_channel()
                
        except KeyboardInterrupt:
            logger.info("بات متوقف شد")
        except Exception as e:
            logger.error(f"خطای کلی: {e}")
        finally:
            if self.session:
                await self.session.close()

if __name__ == '__main__':
    logger.info("در حال راه‌اندازی Bitcoin Price Bot...")
    bot = BitcoinPriceBot(BOT_TOKEN, CHANNEL_USERNAME)
    asyncio.run(bot.start())
