"""
Bot de Telegram para notificaciones de bajada de precio.
Usa la API de Telegram directamente via httpx (sin librerías extra).
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send(self, message: str) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            r = httpx.post(url, json=payload, timeout=10)
            r.raise_for_status()
            logger.info("Telegram: mensaje enviado OK")
            return True
        except httpx.HTTPError as e:
            logger.error("Telegram: error enviando mensaje: %s", e)
            return False

    def notify_price_drop(
        self,
        product_name: str,
        current_price: float,
        previous_price: float,
        target_price: float,
        url: str,
        source: str,
        condition: str = "new",
    ):
        drop_pct = ((previous_price - current_price) / previous_price) * 100
        emoji_condition = "🔵 Segunda mano" if condition == "used" else "🟢 Nuevo"
        below_target = current_price <= target_price

        msg = (
            f"{'🚨 BAJADA DE PRECIO' if below_target else '📉 Bajada detectada'}\n\n"
            f"<b>{product_name}</b>\n"
            f"{emoji_condition}\n\n"
            f"💰 Precio actual:  <b>{current_price:.2f}€</b>\n"
            f"📊 Precio anterior: {previous_price:.2f}€\n"
            f"📉 Bajada: -{drop_pct:.1f}%\n"
            f"🎯 Tu objetivo: {target_price:.2f}€\n\n"
            f"🛒 <a href=\"{url}\">Ver en {source}</a>"
        )
        if below_target:
            msg += "\n\n✅ <b>¡ESTÁ POR DEBAJO DE TU PRECIO OBJETIVO!</b>"

        self.send(msg)

    def notify_wallapop_alert(
        self,
        product_name: str,
        listings: list[dict],
        target_price: float,
    ):
        """Notifica nuevos anuncios de Wallapop bajo el precio objetivo."""
        if not listings:
            return

        msg = f"🔔 <b>Wallapop — {product_name}</b>\n"
        msg += f"🎯 Objetivo: {target_price:.0f}€\n\n"

        for i, listing in enumerate(listings[:5], 1):  # máximo 5 por mensaje
            msg += (
                f"{i}. {listing['title'][:60]}\n"
                f"   💶 <b>{listing['price']:.0f}€</b>\n\n"
            )

        if len(listings) > 5:
            msg += f"...y {len(listings) - 5} más en Wallapop."

        self.send(msg)

    def notify_summary(self, summary_lines: list[str]):
        """Resumen diario de todos los productos trackeados."""
        msg = "📋 <b>Resumen diario — Price Tracker</b>\n\n"
        msg += "\n".join(summary_lines)
        self.send(msg)