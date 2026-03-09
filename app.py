from fastapi import FastAPI

from bot.telegram_bot import TelegramNotifier
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from db.database import init_db, get_active_products
from tracker import run_cycle, send_summary

app = FastAPI()

init_db()
notifier = TelegramNotifier(
    token=TELEGRAM_TOKEN,
    chat_id=TELEGRAM_CHAT_ID,
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
    send_summary(notifier)
    return {"message": "Summary completed"}


@app.post("/scrape-and-summary")
def scrape_and_summary():
    run_cycle(notifier)
    send_summary(notifier)
    return {"message": "Scraping and summary completed"}


@app.get("/products")
def list_products():
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
                "active": p.active,
            }
            for p in products
        ],
    }