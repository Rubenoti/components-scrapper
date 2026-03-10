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


def _mask_dsn(dsn: str) -> str:
    if "@" not in dsn or "://" not in dsn:
        return dsn
    try:
        prefix, rest = dsn.split("://", 1)
        creds, hostpart = rest.split("@", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{prefix}://{user}:****@{hostpart}"
        return f"{prefix}://****@{hostpart}"
    except Exception:
        return dsn


def _get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "price_tracker")
    user = os.getenv("POSTGRES_USER", "postgres")
    pwd = os.getenv("POSTGRES_PASSWORD", "")

    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


@contextmanager
def get_connection():
    dsn = _get_dsn()
    logger.debug("Abriendo conexión a PostgreSQL: %s", _mask_dsn(dsn))
    conn: PgConnection = psycopg2.connect(
        dsn,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        yield conn
        conn.commit()
        logger.debug("Commit SQL realizado correctamente")
    except Exception as e:
        conn.rollback()
        logger.exception("Rollback SQL por error: %s", e)
        raise
    finally:
        conn.close()
        logger.debug("Conexión PostgreSQL cerrada")


def _normalize_row(row: dict) -> dict:
    return {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in dict(row).items()
    }


def init_db():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                logger.info("Inicializando tablas e índices...")
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
                """)

                cur.execute("""
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
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_price_records_product
                    ON price_records(product_id, scraped_at DESC);
                """)

                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_products_name_source_url
                    ON products(name, source, url);
                """)

        logger.info("PostgreSQL inicializado correctamente")
    except Exception as e:
        logger.exception("Error al inicializar tablas: %s", e)
        raise


def upsert_product(p: Product) -> int:
    logger.info(
        "Upsert product: name='%s' source='%s' category='%s' active=%s target=%.2f",
        p.name, p.source, p.category, p.active, float(p.target_price)
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products (name, url, source, target_price, category, notes, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name, source, url)
                DO UPDATE SET
                    target_price = EXCLUDED.target_price,
                    category = EXCLUDED.category,
                    notes = EXCLUDED.notes,
                    active = EXCLUDED.active
                RETURNING id
                """,
                (
                    p.name,
                    p.url,
                    p.source,
                    p.target_price,
                    p.category,
                    p.notes,
                    p.active,
                ),
            )
            product_id = cur.fetchone()["id"]
            logger.info("Producto persistido con id=%s", product_id)
            return product_id


def save_price(record: PriceRecord):
    logger.info(
        "Insertando price_record: product_id=%s price=%.2f currency=%s in_stock=%s condition=%s scraped_at=%s title='%s'",
        record.product_id,
        float(record.price),
        record.currency,
        record.in_stock,
        record.condition,
        record.scraped_at,
        (record.raw_title or "")[:80],
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO price_records
                    (product_id, price, currency, in_stock, scraped_at, raw_title, condition)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    record.product_id,
                    record.price,
                    record.currency,
                    record.in_stock,
                    record.scraped_at,
                    record.raw_title,
                    record.condition,
                ),
            )
            row_id = cur.fetchone()["id"]
            logger.info("price_record insertado con id=%s", row_id)


def get_active_products() -> list[Product]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE active = TRUE ORDER BY id ASC")
            rows = cur.fetchall()

    products = [Product(**_normalize_row(r)) for r in rows]
    logger.info("Productos activos recuperados: %d", len(products))
    return products


def get_last_price(product_id: int) -> Optional[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM price_records
                WHERE product_id = %s
                ORDER BY scraped_at DESC, id DESC
                LIMIT 1
                """,
                (product_id,),
            )
            row = cur.fetchone()

    record = PriceRecord(**_normalize_row(row)) if row else None
    logger.debug("Último precio product_id=%s -> %s", product_id, record.price if record else None)
    return record


def get_today_price(product_id: int) -> Optional[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM price_records
                WHERE product_id = %s
                  AND DATE(scraped_at AT TIME ZONE 'UTC') = DATE(NOW() AT TIME ZONE 'UTC')
                ORDER BY scraped_at DESC, id DESC
                LIMIT 1
                """,
                (product_id,),
            )
            row = cur.fetchone()

    record = PriceRecord(**_normalize_row(row)) if row else None
    logger.info("Precio de hoy product_id=%s -> %s", product_id, record.price if record else None)
    return record


def get_yesterday_price(product_id: int) -> Optional[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM price_records
                WHERE product_id = %s
                  AND DATE(scraped_at AT TIME ZONE 'UTC') = DATE((NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day')
                ORDER BY scraped_at DESC, id DESC
                LIMIT 1
                """,
                (product_id,),
            )
            row = cur.fetchone()

    record = PriceRecord(**_normalize_row(row)) if row else None
    logger.info("Precio de ayer product_id=%s -> %s", product_id, record.price if record else None)
    return record


def get_price_history(product_id: int, limit: int = 30) -> list[PriceRecord]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM price_records
                WHERE product_id = %s
                ORDER BY scraped_at DESC, id DESC
                LIMIT %s
                """,
                (product_id, limit),
            )
            rows = cur.fetchall()

    history = [PriceRecord(**_normalize_row(r)) for r in rows]
    logger.info("Histórico recuperado para product_id=%s -> %d filas", product_id, len(history))
    return history


def get_min_price(product_id: int) -> Optional[float]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MIN(price) AS min_price FROM price_records WHERE product_id = %s",
                (product_id,),
            )
            row = cur.fetchone()

    value = float(row["min_price"]) if row and row["min_price"] is not None else None
    logger.info("Precio mínimo para product_id=%s -> %s", product_id, value)
    return value