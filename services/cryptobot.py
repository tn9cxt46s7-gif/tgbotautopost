"""CryptoBot (Crypto Pay) client — fast auto crypto payments."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import CRYPTO_BOT_TOKEN, CRYPTO_BOT_API, CRYPTO_BOT_ASSET, CRYPTO_BOT_FIAT

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8, connect=3)
_session: aiohttp.ClientSession | None = None


def cryptobot_configured() -> bool:
    return bool(CRYPTO_BOT_TOKEN)


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=_TIMEOUT)
    return _session


async def _api(method: str, **params) -> dict[str, Any]:
    if not CRYPTO_BOT_TOKEN:
        raise RuntimeError("CRYPTO_BOT_TOKEN not set")
    url = f"{CRYPTO_BOT_API.rstrip('/')}/{method}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    session = await _get_session()
    async with session.post(url, json=params or None, headers=headers) as resp:
        data = await resp.json(content_type=None)
    if not data.get("ok"):
        err = data.get("error", data)
        raise RuntimeError(f"CryptoBot API error: {err}")
    return data["result"]


async def create_invoice(
    *,
    amount_eur: int | float,
    description: str,
    payload: str,
    paid_btn_url: str | None = None,
) -> dict[str, Any]:
    """Create invoice — prefer direct USDT (1 round-trip), then fiat EUR."""
    amount = str(round(float(amount_eur), 2))
    base: dict[str, Any] = {
        "description": description[:1024],
        "payload": payload[:4096],
        "allow_comments": False,
        "allow_anonymous": True,
    }
    if paid_btn_url:
        base["paid_btn_name"] = "callback"
        base["paid_btn_url"] = paid_btn_url

    # Fast path: USDT amount ≈ EUR (no exchange-rate round-trip)
    try:
        return await _api(
            "createInvoice",
            asset=CRYPTO_BOT_ASSET or "USDT",
            amount=amount,
            **base,
        )
    except RuntimeError as e:
        logger.warning("CryptoBot USDT invoice failed, trying fiat: %s", e)

    # Fallback: fiat EUR (single call, no rates)
    fiat = CRYPTO_BOT_FIAT or "EUR"
    return await _api(
        "createInvoice",
        currency_type="fiat",
        fiat=fiat,
        amount=amount,
        **base,
    )


async def get_invoice(invoice_id: int | str) -> dict[str, Any] | None:
    result = await _api("getInvoices", invoice_ids=str(invoice_id))
    items = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else None)
    if not items:
        return None
    return items[0]
