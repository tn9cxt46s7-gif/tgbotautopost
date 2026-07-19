from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

scheduler = AsyncIOScheduler()

def start_scheduler(bot):
    scheduler.start()
    print("🕒 Планировщик запущен")

# Здесь будем добавлять задачи автопостинга