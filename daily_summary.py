#!/usr/bin/env python3
import logging

from bot.telegram_bot import TelegramNotifier
from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from db.database import init_db
from tracker import send_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== INICIO SCRIPT daily_summary.py ===")
    init_db()

    notifier = TelegramNotifier(
        token=TELEGRAM_TOKEN,
        chat_id=TELEGRAM_CHAT_ID,
    )

    logger.info("Ejecutando resumen diario...")
    send_summary(notifier)
    logger.info("=== FIN SCRIPT daily_summary.py ===")