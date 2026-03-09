import logging
from datetime import datetime
from typing import List

import httpx

from models.models import PriceRecord

logger = logging.getLogger(__name__)


def search_wallapop(keyword: str, product_id: int, max_price: float) -> List[PriceRecord]:
    """
    Busca anuncios en Wallapop.
    Si falla la búsqueda, devuelve lista vacía en lugar de inventar precios.
    """

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

    try:
        response = httpx.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.error("Error buscando en Wallapop: %s", e)
        return []

    items = data.get("search_objects", []) or data.get("items", [])
    results: List[PriceRecord] = []

    for item in items:
        try:
            price_info = item.get("price", {})
            if isinstance(price_info, dict):
                price = float(price_info.get("amount", 0))
            else:
                price = float(price_info)

            title = item.get("title") or item.get("description") or keyword

            results.append(
                PriceRecord(
                    id=None,
                    product_id=product_id,
                    price=price,
                    currency="EUR",
                    in_stock=True,
                    scraped_at=datetime.now(),
                    raw_title=title,
                    condition="used",
                )
            )
        except (TypeError, ValueError):
            continue

    logger.info("Wallapop: %d resultados válidos para '%s'", len(results), keyword)
    return results