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
    
    # Scraping diario a las 10:55 para tener datos frescos
    scheduler.add_job(run_cycle, CronTrigger(hour=10, minute=55), args=[notifier], id="daily_scrape")
    # Resumen diario a las 11:00
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
    """Ejecuta scraping y envía el resumen a Telegram."""
    run_cycle(notifier)
    run_summary(notifier)
    return {"message": "Scraping and summary completed"}

@app.get("/products")
def list_products():
    """Endpoint para ver todos los productos en la BD."""
    from db.database import get_active_products
    products = get_active_products()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "source": p.source,
                "target_price": float(p.target_price),
                "url": p.url,
                "active": p.active
            }
            for p in products
        ]
    }