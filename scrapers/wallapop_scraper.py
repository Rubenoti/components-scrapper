import logging
from datetime import datetime
from typing import List

import httpx

from models.product import PriceRecord

logger = logging.getLogger(__name__)


def search_wallapop(keyword: str, product_id: int, max_price: float) -> List[PriceRecord]:
    min_price = 1
    url = "https://api.wallapop.com/api/v3/general/search"

    params = {
        "keywords": keyword,
        "min_sale_price": min_price,
        "max_sale_price": max_price,
        "order_by": "price_asc",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    logger.info(
        "Buscando Wallapop product_id=%s keyword='%s' max_price=%.2f",
        product_id, keyword, max_price
    )

    try:
        response = httpx.get(url, params=params, headers=headers, timeout=20)
        logger.info("Wallapop status_code=%s url=%s", response.status_code, str(response.url))
        response.raise_for_status()
        data = response.json()
        logger.info("Wallapop JSON keys: %s", list(data.keys())[:20])
    except (httpx.HTTPError, ValueError) as e:
        logger.exception("Error buscando en Wallapop product_id=%s keyword='%s': %s", product_id, keyword, e)
        return []

    items = data.get("search_objects", []) or data.get("items", [])
    logger.info("Wallapop items brutos recibidos: %d", len(items))

    results: List[PriceRecord] = []

    for index, item in enumerate(items, 1):
        try:
            price_info = item.get("price", {})
            if isinstance(price_info, dict):
                price = float(price_info.get("amount", 0))
            else:
                price = float(price_info)

            title = item.get("title") or item.get("description") or keyword

            record = PriceRecord(
                id=None,
                product_id=product_id,
                price=price,
                currency="EUR",
                in_stock=True,
                scraped_at=datetime.now(),
                raw_title=title,
                condition="used",
            )
            results.append(record)

            logger.debug(
                "Wallapop item #%d parseado -> %.2f€ '%s'",
                index, price, title[:80]
            )
        except (TypeError, ValueError) as e:
            logger.warning("Item Wallapop inválido #%d para '%s': %s", index, keyword, e)
            continue

    logger.info("Wallapop: %d resultados válidos para '%s'", len(results), keyword)
    return results