import argparse
import logging
from typing import Optional

from config.settings import MIN_DROP_PCT_TO_NOTIFY
from db.database import (
    init_db,
    get_active_products,
    save_price,
    get_last_price,
    get_today_price,
    get_yesterday_price,
)
from models.product import PriceRecord
from bot.telegram_bot import TelegramNotifier

try:
    from scrapers.camel_scraper import scrape_camel
except Exception:
    scrape_camel = None

from scrapers.pccomponentes_scraper import scrape_pccomponentes
from scrapers.wallapop_scraper import search_wallapop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_cycle(notifier: TelegramNotifier):
    logger.info("=== INICIO TRACKER CYCLE ===")
    products = get_active_products()
    logger.info("Productos activos a procesar: %d", len(products))

    processed = 0
    saved = 0
    skipped = 0

    for product in products:
        logger.info(
            "Procesando product_id=%s name='%s' source='%s' url='%s'",
            product.id, product.name, product.source, product.url
        )

        processed += 1
        target_price = float(product.target_price)
        previous_price = get_last_price(product.id)

        if previous_price:
            logger.info(
                "Último precio previo para product_id=%s -> %.2f€",
                product.id, previous_price.price
            )
        else:
            logger.info("No existe precio previo para product_id=%s", product.id)

        new_record: Optional[PriceRecord] = None

        if product.source == "amazon":
            if scrape_camel is None:
                logger.warning("Scraper Amazon/Camel no implementado; se omite '%s'", product.name)
                skipped += 1
                continue
            new_record = scrape_camel(product.url, product.id)

        elif product.source == "pccomponentes":
            new_record = scrape_pccomponentes(product.url, product.id)

        elif product.source == "wallapop":
            listings = search_wallapop(
                keyword=product.name,
                product_id=product.id,
                max_price=target_price * 1.3,
            )

            logger.info("Wallapop devolvió %d resultados para '%s'", len(listings), product.name)

            if listings:
                cheapest = min(listings, key=lambda r: r.price)
                logger.info(
                    "Resultado más barato Wallapop para product_id=%s -> %.2f€ ('%s')",
                    product.id,
                    cheapest.price,
                    cheapest.raw_title[:80],
                )
                save_price(cheapest)
                saved += 1

                below_target = [l for l in listings if l.price <= target_price]
                logger.info(
                    "Resultados Wallapop por debajo del objetivo %.2f€: %d",
                    target_price,
                    len(below_target),
                )
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
                logger.warning("Sin resultados válidos en Wallapop para '%s'", product.name)

            continue

        else:
            logger.warning("Source no soportado '%s' para product_id=%s", product.source, product.id)
            skipped += 1
            continue

        if new_record is None:
            logger.warning("Sin datos scrapeados para '%s'; se omite insert", product.name)
            skipped += 1
            continue

        logger.info(
            "Nuevo precio scrapeado para product_id=%s -> %.2f€",
            product.id,
            new_record.price,
        )
        save_price(new_record)
        saved += 1

        if previous_price and previous_price.price > 0:
            drop_pct = ((previous_price.price - new_record.price) / previous_price.price) * 100

            logger.info(
                "Comparativa inmediata product_id=%s | anterior=%.2f€ | nuevo=%.2f€ | delta_pct=%.2f%%",
                product.id,
                previous_price.price,
                new_record.price,
                drop_pct,
            )

            if drop_pct >= MIN_DROP_PCT_TO_NOTIFY:
                logger.info(
                    "Se cumple umbral de alerta %.2f%% para product_id=%s; enviando Telegram",
                    MIN_DROP_PCT_TO_NOTIFY,
                    product.id,
                )
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
            logger.info("Primera referencia para '%s'; no se calcula bajada", product.name)

    logger.info(
        "=== FIN TRACKER CYCLE === procesados=%d guardados=%d omitidos=%d",
        processed, saved, skipped
    )


def send_summary(notifier: TelegramNotifier):
    logger.info("=== INICIO DAILY SUMMARY ===")
    products = get_active_products()
    logger.info("Productos activos para resumen: %d", len(products))

    lines = ["📊 <b>Resumen diario de precios</b>"]

    for product in products:
        logger.info("Resumen para product_id=%s name='%s'", product.id, product.name)

        current = get_today_price(product.id)
        previous = get_yesterday_price(product.id)

        if current is None:
            logger.warning("No hay precio de hoy para product_id=%s", product.id)
            lines.append(f"• {product.name}: sin datos de hoy")
            continue

        logger.info(
            "Datos resumen product_id=%s | hoy=%s | ayer=%s",
            product.id,
            current.price if current else None,
            previous.price if previous else None,
        )

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
            trend = "🆕 sin dato de ayer"

        lines.append(
            f"• <b>{product.name}</b>\n"
            f"  Actual: {current.price:.2f}€ | Objetivo: {float(product.target_price):.2f}€\n"
            f"  Estado: {trend}"
        )

    message = "\n".join(lines)
    logger.info("Resumen generado:\n%s", message)

    ok = notifier.send_message(message)
    logger.info("Resultado envío resumen Telegram: %s", ok)
    logger.info("=== FIN DAILY SUMMARY ===")


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
    logger.info("Arranque tracker.py con args.summary=%s", args.summary)

    init_db()
    notifier = TelegramNotifier()

    if args.summary:
        send_summary(notifier)
    else:
        run_cycle(notifier)


if __name__ == "__main__":
    main()