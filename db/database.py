import logging
import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from models.product import Product, PriceRecord

logger = logging.getLogger(__name__)


def _get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn
    # Construcción desde variables individuales
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB",   "price_tracker")
    user = os.getenv("POSTGRES_USER", "postgres")
    pwd  = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


@contextmanager
def get_connection():
    conn: PgConnection = psycopg2.connect(
        _get_dsn(),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea las tablas y el índice si no existen."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        id           SERIAL PRIMARY KEY,
                        name         TEXT NOT NULL,
                        url          TEXT NOT NULL DEFAULT '',
                        source       TEXT NOT NULL,
                        target_price NUMERIC(10,2) NOT NULL,
                        category     TEXT NOT NULL,
                        notes        TEXT DEFAULT '',
                        active       BOOLEAN DEFAULT TRUE,
                        created_at   TIMESTAMPTZ DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS price_records (
                        id         SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        price      NUMERIC(10,2) NOT NULL,
                        currency   TEXT DEFAULT 'EUR',
                        in_stock   BOOLEAN DEFAULT TRUE,
                        scraped_at TIMESTAMPTZ DEFAULT NOW(),
                        raw_title  TEXT DEFAULT '',
                        condition  TEXT DEFAULT 'new'
                    );

                    CREATE INDEX IF NOT EXISTS idx_price_records_product
                        ON price_records(product_id, scraped_at DESC);
                """)
        logger.info("PostgreSQL: tablas inicializadas — DSN: %s", _get_dsn())
    except Exception as e:
        logger.warning("Error al inicializar tablas (posiblemente ya existen): %s", e)


def upsert_product(p: Product) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO products (name, url, source, target_price, category, notes, active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (p.name, p.url, p.source, p.target_price, p.category, p.notes, p.active)
            )
            return cur.fetchone()["id"]


def save_price(record: PriceRecord):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO price_records
                       (product_id, price, currency, in_stock, scraped_at, raw_title, condition)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (record.product_id, record.price, record.currency, record.in_stock,
                 record.scraped_at, record.raw_title, record.condition)
            )


def get_active_products() -> list[Product]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE active = TRUE")
            rows = cur.fetchall()
    return [Product(**{k: float(v) if isinstance(v, Decimal) else v for k, v in dict(r).items()}) for r in rows]


def get_last_price(product_id: int) -> Optional[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM price_records
                   WHERE product_id = %s
                   ORDER BY scraped_at DESC LIMIT 1""",
                (product_id,)
            )
            row = cur.fetchone()
    return PriceRecord(**{k: float(v) if isinstance(v, Decimal) else v for k, v in dict(row).items()}) if row else None


def get_price_history(product_id: int, limit: int = 30) -> list[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM price_records
                   WHERE product_id = %s
                   ORDER BY scraped_at DESC LIMIT %s""",
                (product_id, limit)
            )
            rows = cur.fetchall()
    return [PriceRecord(**{k: float(v) if isinstance(v, Decimal) else v for k, v in dict(r).items()}) for r in rows]


def get_min_price(product_id: int) -> Optional[float]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(price) AS min_price FROM price_records WHERE product_id = %s",
                (product_id,)
            )
            row = cur.fetchone()
    return float(row["min_price"]) if row and row["min_price"] is not None else None


def get_yesterday_price(product_id: int) -> Optional[PriceRecord]:
    """Obtiene el último precio registrado ayer (día anterior)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM price_records
                   WHERE product_id = %s AND DATE(scraped_at) < DATE(NOW())
                   ORDER BY scraped_at DESC LIMIT 1""",
                (product_id,)
            )
            row = cur.fetchone()
    return PriceRecord(**{k: float(v) if isinstance(v, Decimal) else v for k, v in dict(row).items()}) if row else None