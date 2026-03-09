#!/usr/bin/env python3
"""
Script para ejecutar el resumen diario automáticamente.
Se ejecuta vía cron en Railway.
"""
import logging
from tracker import run_summary
from bot.telegram_bot import TelegramNotifier
from config.settings import load_settings
from db.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    settings = load_settings()
    init_db()

    notifier = TelegramNotifier(
        token=settings["telegram_token"],
        chat_id=settings["telegram_chat_id"],
    )

    logger.info("Ejecutando resumen diario...")
    run_summary(notifier)
    logger.info("Resumen diario enviado.")