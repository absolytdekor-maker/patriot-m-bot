
import asyncio
from datetime import datetime
from backup import backup_db

async def scheduler():
    while True:
        now = datetime.now()
        if now.hour == 3 and now.minute == 0:
            backup_db()
            await asyncio.sleep(60)
        await asyncio.sleep(30)
