import re
import logging
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from models.models import PriceRecord

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
            return price

    html = soup.get_text(" ", strip=True)
    match = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*€', html)
    if match:
        return _normalize_price(match.group(1))

    return None


def _parse_stock(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()

    negative_signals = [
        "agotado",
        "sin stock",
        "no disponible",
        "próximamente",
    ]

    return not any(signal in text for signal in negative_signals)


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
                return content.strip()

        text = node.get_text(" ", strip=True)
        if text:
            return text

    return "Producto en PcComponentes"


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