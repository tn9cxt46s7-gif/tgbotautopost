"""CryptoBot (Crypto Pay) client — auto crypto payments."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import CRYPTO_BOT_TOKEN, CRYPTO_BOT_API, CRYPTO_BOT_ASSET

logger = logging.getLogger(__name__)


def cryptobot_configured() -> bool:
    return bool(CRYPTO_BOT_TOKEN)


async def _api(method: str, **params) -> dict[str, Any]:
    if not CRYPTO_BOT_TOKEN:
        raise RuntimeError("CRYPTO_BOT_TOKEN not set")
    url = f"{CRYPTO_BOT_API.rstrip('/')}/{method}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params or None, headers=headers, timeout=30) as resp:
            data = await resp.json(content_type=None)
    if not data.get("ok"):
        err = data.get("error", data)
        raise RuntimeError(f"CryptoBot API error: {err}")
    return data["result"]


async def create_invoice(
    *,
    amount_rub: int,
    description: str,
    payload: str,
    paid_btn_url: str | None = None,
) -> dict[str, Any]:
    """
    Create USDT invoice. amount_rub converted roughly via exchange rates,
    or we pass fiat if API supports currency_type=fiat.
    Prefer fiat RUB when supported.
    """
    params: dict[str, Any] = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": str(amount_rub),
        "description": description[:1024],
        "payload": payload[:4096],
        "allow_comments": False,
        "allow_anonymous": True,
    }
    if paid_btn_url:
        params["paid_btn_name"] = "callback"
        params["paid_btn_url"] = paid_btn_url
    try:
        return await _api("createInvoice", **params)
    except RuntimeError:
        # Fallback: crypto asset amount (USDT ≈ amount_rub / 90 rough; better use rates)
        rates = await _api("getExchangeRates")
        usdt_rub = None
        for row in rates or []:
            if row.get("source") == "USDT" and row.get("target") == "RUB" and row.get("is_valid"):
                usdt_rub = float(row["rate"])
                break
        if not usdt_rub or usdt_rub <= 0:
            usdt_rub = 90.0
        amount_usdt = round(amount_rub / usdt_rub, 2)
        params = {
            "asset": CRYPTO_BOT_ASSET,
            "amount": str(amount_usdt),
            "description": description[:1024],
            "payload": payload[:4096],
            "allow_comments": False,
            "allow_anonymous": True,
        }
        if paid_btn_url:
            params["paid_btn_name"] = "callback"
            params["paid_btn_url"] = paid_btn_url
        return await _api("createInvoice", **params)


async def get_invoice(invoice_id: int | str) -> dict[str, Any] | None:
    result = await _api("getInvoices", invoice_ids=str(invoice_id))
    items = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else None)
    if not items:
        return None
    return items[0]
