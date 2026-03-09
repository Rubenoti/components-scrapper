from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from tracker import run_cycle, run_summary
from bot.telegram_bot import TelegramNotifier
from config.settings import load_settings
from db.database import init_db

settings = None
notifier = None
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global settings, notifier
    settings = load_settings()
    init_db()
    notifier = TelegramNotifier(
        token=settings["telegram_token"],
        chat_id=settings["telegram_chat_id"],
    )
    
    # Programar resumen diario a las 11:00
    scheduler.add_job(run_summary, CronTrigger(hour=11, minute=0), args=[notifier], id="daily_summary")
    scheduler.start()
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Price Tracker API"}

@app.post("/scrape")
def scrape():
    run_cycle(notifier)
    return {"message": "Scraping cycle completed"}

@app.post("/summary")
def summary():
    run_summary(notifier)
    return {"message": "Daily summary sent"}