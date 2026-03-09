"""
Scraper para PcComponentes.
Extrae precio y disponibilidad de páginas de producto.
"""
import re
import logging
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from models.product import PriceRecord

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scrape_pccomponentes(url: str, product_id: int) -> Optional[PriceRecord]:
    logger.info("Scrapeando PcComponentes: %s", url)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Error HTTP en PcComponentes: %s", e)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    price = _parse_price(soup)
    if price is None:
        logger.warning("No se encontró precio en PcComponentes para %s", url)
        return None

    in_stock = _parse_stock(soup)
    title = _parse_title(soup)

    return PriceRecord(
        id=None,
        product_id=product_id,
        price=price,
        currency="EUR",
        in_stock=in_stock,
        scraped_at=datetime.now(),
        raw_title=title,
        condition="new",
    )


def _parse_price(soup: BeautifulSoup) -> Optional[float]:
    # Selector principal: JSON-LD schema
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price_str = str(offers.get("price", ""))
            if price_str:
                return float(price_str)
        except (json.JSONDecodeError, ValueError, AttributeError):
            continue

    # Fallback: selector CSS del precio visible
    for selector in [
        "[data-e2e='product-price'] .price",
        ".price-container .price",
        "span.price",
        "[itemprop='price']",
    ]:
        tag = soup.select_one(selector)
        if tag:
            price = _text_to_float(tag.get_text(strip=True))
            if price:
                return price

    return None


def _parse_stock(soup: BeautifulSoup) -> bool:
    # Busca indicadores de stock
    out_of_stock_signals = ["sin stock", "agotado", "no disponible", "out of stock"]
    page_text = soup.get_text().lower()
    return not any(signal in page_text for signal in out_of_stock_signals)


def _parse_title(soup: BeautifulSoup) -> str:
    tag = soup.select_one("h1") or soup.find("title")
    return tag.get_text(strip=True)[:200] if tag else ""


def _text_to_float(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d,.]", "", text)
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None