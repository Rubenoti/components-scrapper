from fastapi import FastAPI
from tracker import run_cycle, run_summary
from bot.telegram_bot import TelegramNotifier
from config.settings import load_settings
from db.database import init_db

app = FastAPI()

settings = load_settings()
init_db()

notifier = TelegramNotifier(
    token=settings["telegram_token"],
    chat_id=settings["telegram_chat_id"],
)

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