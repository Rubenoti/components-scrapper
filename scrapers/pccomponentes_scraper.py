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
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _normalize_price(text: str) -> Optional[float]:
    if not text:
        return None

    text = text.strip()
    text = text.replace("€", "")
    text = text.replace("\xa0", "")
    text = text.replace(".", "")
    text = text.replace(",", ".")
    text = re.sub(r"[^\d.]", "", text)

    try:
        return float(text)
    except ValueError:
        return None


def _parse_price(soup: BeautifulSoup) -> Optional[float]:
    selectors = [
        '[data-testid="price-current"]',
        '.priceCurrent',
        '.price',
        '.buybox__price',
        '[itemprop="price"]',
        'meta[itemprop="price"]',
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue

        if node.name == "meta":
            content = node.get("content")
            price = _normalize_price(content or "")
        else:
            price = _normalize_price(node.get_text(" ", strip=True))

        if price is not None:
            logger.info("Precio detectado por selector '%s': %.2f€", selector, price)
            return price

    html = soup.get_text(" ", strip=True)
    match = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*€', html)
    if match:
        price = _normalize_price(match.group(1))
        logger.info("Precio detectado por regex fallback: %s", price)
        return price

    return None


def _parse_stock(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()

    negative_signals = [
        "agotado",
        "sin stock",
        "no disponible",
        "próximamente",
    ]

    in_stock = not any(signal in text for signal in negative_signals)
    logger.info("Stock detectado: %s", in_stock)
    return in_stock


def _parse_title(soup: BeautifulSoup) -> str:
    selectors = [
        "h1",
        '[data-testid="product-name"]',
        ".product-name",
        'meta[property="og:title"]',
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue

        if node.name == "meta":
            content = node.get("content")
            if content:
                logger.info("Título detectado por selector '%s': %s", selector, content[:80])
                return content.strip()

        text = node.get_text(" ", strip=True)
        if text:
            logger.info("Título detectado por selector '%s': %s", selector, text[:80])
            return text

    return "Producto en PcComponentes"


def scrape_pccomponentes(url: str, product_id: int) -> Optional[PriceRecord]:
    logger.info("Scrapeando PcComponentes product_id=%s url=%s", product_id, url)

    try:
        response = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        logger.info("PcComponentes status_code=%s final_url=%s", response.status_code, str(response.url))
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.exception("Error HTTP en PcComponentes para product_id=%s: %s", product_id, e)
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    price = _parse_price(soup)
    if price is None:
        logger.warning("No se encontró precio en PcComponentes para product_id=%s url=%s", product_id, url)
        return None

    in_stock = _parse_stock(soup)
    title = _parse_title(soup)

    record = PriceRecord(
        id=None,
        product_id=product_id,
        price=price,
        currency="EUR",
        in_stock=in_stock,
        scraped_at=datetime.now(),
        raw_title=title,
        condition="new",
    )
    logger.info("PriceRecord generado PcComponentes: %s", record)
    return record