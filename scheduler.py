import asyncio
import logging
from datetime import datetime
from telegram import Bot
from database import экспорт_в_csv
from config import ТОКЕН_БОТА, ПОЛУЧАТЕЛЬ_ОТЧЁТОВ_ID

logger = logging.getLogger(__name__)

async def отправить_месячный_отчёт():
    bot = Bot(token=ТОКЕН_БОТА)
    try:
        сейчас = datetime.now()
        год = сейчас.year
        месяц = сейчас.month - 1
        if месяц == 0:
            месяц = 12
            год -= 1
        путь = экспорт_в_csv(месяц=месяц, год=год)
        подпись = f"📊 Отчёт за {datetime(год, месяц, 1).strftime('%B %Y')}"
        with open(путь, "rb") as f:
            await bot.send_document(chat_id=ПОЛУЧАТЕЛЬ_ОТЧЁТОВ_ID, document=f, caption=подпись)
        logger.info("Месячный отчёт отправлен.")
    except Exception as e:
        logger.error(f"Ошибка отправки отчёта: {e}")

async def запустить_планировщик():
    while True:
        сейчас = datetime.now()
        if сейчас.day == 1 and сейчас.hour == 10 and сейчас.minute == 0:
            await отправить_месячный_отчёт()
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(60)