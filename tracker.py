import argparse
import logging
import sys
from datetime import datetime

from config.settings import load_settings
from db.database import init_db, get_active_products, save_price, get_last_price, get_min_price, get_yesterday_price
from scrapers.camel_scraper import scrape_camel
from scrapers.pccomponentes_scraper import scrape_pccomponentes
from scrapers.wallapop_scraper import search_wallapop
from bot.telegram_bot import TelegramNotifier
from models.product import PriceRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tracker")

# Umbral mínimo de bajada para notificar (evita ruido por decimales)
MIN_DROP_PCT_TO_NOTIFY = 2.0


def run_cycle(notifier: TelegramNotifier):
    """Ciclo completo: scrape todos los productos activos y notifica si procede."""
    products = get_active_products()
    logger.info("Iniciando ciclo — %d productos activos", len(products))

    for product in products:
        logger.info("Procesando: %s [%s]", product.name, product.source)

        target_price = float(product.target_price)

        new_record: PriceRecord | None = None

        if product.source == "amazon":
            new_record = scrape_camel(product.url, product.id)
        elif product.source == "pccomponentes":
            new_record = scrape_pccomponentes(product.url, product.id)
        elif product.source == "wallapop":
            listings = search_wallapop(
                keyword=product.name,
                product_id=product.id,
                max_price=target_price * 1.3,  # margen del 30% sobre objetivo
            )
            if listings:
                # Guarda el más barato encontrado
                cheapest = min(listings, key=lambda r: r.price)
                save_price(cheapest)
                # Notifica si hay anuncios bajo objetivo
                below_target = [l for l in listings if l.price <= target_price]
                if below_target:
                    notifier.notify_wallapop_alert(
                        product_name=product.name,
                        listings=[{"title": l.raw_title, "price": l.price} for l in below_target],
                        target_price=product.target_price,
                    )
            continue

        if new_record is None:
            logger.warning("Sin datos para %s, saltando.", product.name)
            continue

        save_price(new_record)

        # Compara con el precio anterior para detectar bajadas
        last = get_last_price(product.id)
        if last and last.price > 0:
            drop_pct = ((last.price - new_record.price) / last.price) * 100
            if drop_pct >= MIN_DROP_PCT_TO_NOTIFY:
                notifier.notify_price_drop(
                    product_name=product.name,
                    current_price=new_record.price,
                    previous_price=last.price,
                    target_price=target_price,
                    url=product.url,
                    source=product.source,
                    condition=new_record.condition,
                )


def run_summary(notifier: TelegramNotifier):
    """Resumen diario de todos los productos con su precio actual vs objetivo."""
    products = get_active_products()
    lines = []

    for product in products:
        last = get_last_price(product.id)
        min_price = get_min_price(product.id)
        yesterday = get_yesterday_price(product.id)

        if last:
            target_price = float(product.target_price)
            diff = last.price - target_price
            status = "✅" if diff <= 0 else "⏳"
            yesterday_str = ""
            if yesterday:
                diff_yesterday = last.price - yesterday.price
                yesterday_str = f"\n   Diferencia ayer: {diff_yesterday:+.2f}€"
            lines.append(
                f"{status} <b>{product.name}</b>\n"
                f"   Ahora: {last.price:.2f}€ | Objetivo: {target_price:.2f}€\n"
                f"   Mínimo histórico: {min_price:.2f}€{yesterday_str}"
            )
        else:
            lines.append(f"❓ {product.name} — sin datos aún")

    if lines:
        notifier.notify_summary(lines)
    else:
        logger.info("No hay productos activos para el resumen.")


def main():
    parser = argparse.ArgumentParser(description="Price Tracker")
    parser.add_argument("--summary", action="store_true", help="Envía resumen diario")
    args = parser.parse_args()

    settings = load_settings()
    init_db()

    notifier = TelegramNotifier(
        token=settings["telegram_token"],
        chat_id=settings["telegram_chat_id"],
    )

    if args.summary:
        run_summary(notifier)
    else:
        run_cycle(notifier)


if __name__ == "__main__":
    main()