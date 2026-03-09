import argparse
import logging
from typing import Optional

from config.settings import MIN_DROP_PCT_TO_NOTIFY
from db.database import (
    init_db,
    get_active_products,
    save_price,
    get_last_price,
    get_yesterday_price,
)
from models.product import PriceRecord
from bot.telegram_bot import TelegramNotifier
from scrapers.camel_scraper import scrape_camel
from scrapers.pccomponentes_scraper import scrape_pccomponentes
from scrapers.wallapop_scraper import search_wallapop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_cycle(notifier: TelegramNotifier):
    products = get_active_products()
    logger.info("Iniciando ciclo — %d productos activos", len(products))

    for product in products:
        logger.info("Procesando: %s [%s]", product.name, product.source)

        target_price = float(product.target_price)
        previous_price = get_last_price(product.id)

        new_record: Optional[PriceRecord] = None

        if product.source == "amazon":
            new_record = scrape_camel(product.url, product.id)

        elif product.source == "pccomponentes":
            new_record = scrape_pccomponentes(product.url, product.id)

        elif product.source == "wallapop":
            listings = search_wallapop(
                keyword=product.name,
                product_id=product.id,
                max_price=target_price * 1.3,
            )

            if listings:
                cheapest = min(listings, key=lambda r: r.price)
                save_price(cheapest)

                below_target = [l for l in listings if l.price <= target_price]
                if below_target:
                    notifier.notify_wallapop_alert(
                        product_name=product.name,
                        listings=[
                            {
                                "title": l.raw_title,
                                "price": l.price,
                            }
                            for l in below_target
                        ],
                        target_price=product.target_price,
                    )
            else:
                logger.info("Sin resultados válidos en Wallapop para %s", product.name)

            continue

        if new_record is None:
            logger.warning("Sin datos para %s, saltando.", product.name)
            continue

        save_price(new_record)

        if previous_price and previous_price.price > 0:
            drop_pct = ((previous_price.price - new_record.price) / previous_price.price) * 100

            logger.info(
                "Precio anterior: %.2f€ | nuevo: %.2f€ | bajada: %.2f%%",
                previous_price.price,
                new_record.price,
                drop_pct,
            )

            if drop_pct >= MIN_DROP_PCT_TO_NOTIFY:
                notifier.notify_price_drop(
                    product_name=product.name,
                    current_price=new_record.price,
                    previous_price=previous_price.price,
                    target_price=target_price,
                    url=product.url,
                    source=product.source,
                    condition=new_record.condition,
                )
        else:
            logger.info("No hay precio previo para %s; se guarda como primera referencia.", product.name)


def send_summary(notifier: TelegramNotifier):
    products = get_active_products()
    logger.info("Generando resumen para %d productos activos", len(products))

    lines = ["📊 <b>Resumen diario de precios</b>"]

    for product in products:
        current = get_last_price(product.id)
        previous = get_yesterday_price(product.id)

        if current is None:
            lines.append(f"• {product.name}: sin datos todavía")
            continue

        if previous and previous.price > 0:
            delta = current.price - previous.price
            pct = (delta / previous.price) * 100

            if delta < 0:
                trend = f"🔻 {abs(delta):.2f}€ ({abs(pct):.2f}%)"
            elif delta > 0:
                trend = f"🔺 {abs(delta):.2f}€ ({abs(pct):.2f}%)"
            else:
                trend = "➖ sin cambios"
        else:
            trend = "🆕 primera referencia"

        lines.append(
            f"• <b>{product.name}</b>\n"
            f"  Actual: {current.price:.2f}€ | Objetivo: {float(product.target_price):.2f}€\n"
            f"  Estado: {trend}"
        )

    notifier.send_message("\n".join(lines))


def parse_args():
    parser = argparse.ArgumentParser(description="Price tracker de componentes")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Envía un resumen diario en lugar de ejecutar un ciclo de scraping",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    init_db()
    notifier = TelegramNotifier()

    if args.summary:
        send_summary(notifier)
    else:
        run_cycle(notifier)


if __name__ == "__main__":
    main()