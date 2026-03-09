from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    id: Optional[int]
    name: str
    url: str
    source: str
    target_price: float
    category: str
    notes: str = ""
    active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class PriceRecord:
    product_id: int
    price: float
    currency: str = "EUR"
    in_stock: bool = True
    scraped_at: Optional[datetime] = None
    raw_title: str = ""
    condition: str = "new"
    id: Optional[int] = None