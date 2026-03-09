import logging
from typing import Optional

import httpx

from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID

        if not self.token or not self.chat_id:
            raise ValueError(
                "TelegramNotifier requiere TELEGRAM_TOKEN y TELEGRAM_CHAT_ID"
            )

        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, message: str) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            response = httpx.post(url, json=payload, timeout=15)
            response.raise_for_status()
            logger.info("Telegram: mensaje enviado OK")
            return True
        except httpx.HTTPError as e:
            logger.error("Telegram: error enviando mensaje: %s", e)
            return False

    def send(self, message: str) -> bool:
        return self.send_message(message)

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
            f"💰 Precio actual: <b>{current_price:.2f}€</b>\n"
            f"📊 Precio anterior: {previous_price:.2f}€\n"
            f"📉 Bajada: -{drop_pct:.1f}%\n"
            f"🎯 Tu objetivo: {target_price:.2f}€\n\n"
            f"🛒 <a href=\"{url}\">Ver en {source}</a>"
        )

        if below_target:
            msg += "\n\n✅ <b>¡ESTÁ POR DEBAJO DE TU PRECIO OBJETIVO!</b>"

        self.send_message(msg)

    def notify_wallapop_alert(
        self,
        product_name: str,
        listings: list[dict],
        target_price: float,
    ):
        if not listings:
            return

        msg = f"🔔 <b>Wallapop — {product_name}</b>\n"
        msg += f"🎯 Objetivo: {target_price:.0f}€\n\n"

        for i, listing in enumerate(listings[:5], 1):
            title = listing.get("title", "Sin título")
            price = float(listing.get("price", 0))

            msg += (
                f"{i}. {title[:60]}\n"
                f"   💶 <b>{price:.0f}€</b>\n\n"
            )

        if len(listings) > 5:
            msg += f"...y {len(listings) - 5} más en Wallapop."

        self.send_message(msg)