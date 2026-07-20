"""Telethon helpers: encrypt sessions, login, post as the client's account."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
from io import BytesIO

from cryptography.fernet import Fernet, InvalidToken
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    ChannelPrivateError,
    AuthKeyError,
)
from telethon.sessions import StringSession

from config import TG_API_ID, TG_API_HASH, SESSION_SECRET

logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"^\+\d{10,15}$")


class AccountError(Exception):
    """User-facing auth/post error."""


class Need2FA(AccountError):
    """Code accepted but cloud password required; carry updated session."""

    def __init__(self, pending_session: str):
        super().__init__("Нужен облачный пароль")
        self.pending_session = pending_session


def api_configured() -> bool:
    return bool(TG_API_ID and TG_API_HASH)


def _fernet() -> Fernet:
    digest = hashlib.sha256(SESSION_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_session(raw: str) -> str:
    return _fernet().encrypt(raw.encode("utf-8")).decode("utf-8")


def decrypt_session(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise AccountError("Сессия повреждена. Привяжи аккаунт заново.") from e


def normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]
    if not phone.startswith("+"):
        phone = "+" + phone
    if not _PHONE_RE.match(phone):
        raise AccountError("Телефон в формате +79001234567")
    return phone


def mask_phone(phone: str | None) -> str:
    if not phone or len(phone) < 6:
        return phone or "—"
    return phone[:3] + "***" + phone[-2:]


def _new_client(session: str = "") -> TelegramClient:
    if not api_configured():
        raise AccountError("Подключение временно недоступно. Напиши в поддержку.")
    return TelegramClient(StringSession(session), TG_API_ID, TG_API_HASH)


def make_qr_png(url: str) -> bytes:
    import qrcode
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# Active QR logins: telegram_id -> TelegramClient still connected with qr_login
_qr_clients: dict[int, TelegramClient] = {}


async def cancel_qr_login(telegram_id: int) -> None:
    client = _qr_clients.pop(telegram_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass


async def begin_qr_login(telegram_id: int) -> tuple[str, bytes]:
    """Start QR login. Returns (tg_login_url, png_bytes). Keeps client connected until wait/cancel."""
    await cancel_qr_login(telegram_id)
    client = _new_client()
    await client.connect()
    try:
        qr = await client.qr_login()
        _qr_clients[telegram_id] = client
        # stash qr object on client for wait
        client._eb_qr = qr  # type: ignore[attr-defined]
        return qr.url, make_qr_png(qr.url)
    except Exception:
        await client.disconnect()
        raise


async def wait_qr_login(telegram_id: int, timeout: float = 90) -> tuple[str, str | None]:
    """
    Wait until user scans QR. Returns (raw_session, display_name).
    Raises Need2FA or AccountError.
    """
    client = _qr_clients.get(telegram_id)
    if not client:
        raise AccountError("QR устарел. Нажми «Подключить через QR» снова.")
    qr = getattr(client, "_eb_qr", None)
    if qr is None:
        await cancel_qr_login(telegram_id)
        raise AccountError("QR устарел. Начни снова.")

    try:
        try:
            await qr.wait(timeout=timeout)
        except SessionPasswordNeededError as e:
            pending = client.session.save()
            await cancel_qr_login(telegram_id)
            raise Need2FA(pending) from e
        except asyncio.TimeoutError as e:
            await cancel_qr_login(telegram_id)
            raise AccountError("Время QR вышло. Нажми «Подключить через QR» ещё раз.") from e

        me = await client.get_me()
        name = " ".join(x for x in [me.first_name, me.last_name] if x) or me.username or str(me.id)
        raw = client.session.save()
        await cancel_qr_login(telegram_id)
        return raw, name
    except Need2FA:
        raise
    except AccountError:
        raise
    except Exception:
        await cancel_qr_login(telegram_id)
        raise


async def finish_password_login(pending_session: str, password: str) -> tuple[str, str | None]:
    """Complete 2FA after phone or QR login."""
    client = _new_client(pending_session)
    await client.connect()
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        name = " ".join(x for x in [me.first_name, me.last_name] if x) or me.username or str(me.id)
        return client.session.save(), name
    except SessionPasswordNeededError as e:
        raise AccountError("Неверный облачный пароль.") from e
    finally:
        await client.disconnect()


async def start_phone_login(phone: str) -> tuple[str, str]:
    """Send login code. Returns (pending_session, phone_code_hash)."""
    phone = normalize_phone(phone)
    client = _new_client()
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        pending = client.session.save()
        return pending, sent.phone_code_hash
    finally:
        await client.disconnect()


async def complete_phone_login(
    phone: str,
    code: str,
    phone_code_hash: str,
    pending_session: str,
    password: str | None = None,
) -> tuple[str, str | None]:
    """
    Finish phone login. Returns (raw_session_string, display_name).
    Raises Need2FA if cloud password is required.
    """
    if password is not None:
        return await finish_password_login(pending_session, password)

    phone = normalize_phone(phone)
    code = (code or "").strip().replace(" ", "")
    client = _new_client(pending_session)
    await client.connect()
    try:
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError as e:
            raise Need2FA(client.session.save()) from e
        except PhoneCodeInvalidError as e:
            raise AccountError("Неверный код. Попробуй ещё раз.") from e
        except PhoneCodeExpiredError as e:
            raise AccountError("Код устарел. Начни подключение заново.") from e

        me = await client.get_me()
        name = " ".join(x for x in [me.first_name, me.last_name] if x) or me.username or str(me.id)
        return client.session.save(), name
    finally:
        await client.disconnect()


async def verify_session(raw_session: str) -> str | None:
    client = _new_client(raw_session)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            return None
        me = await client.get_me()
        return " ".join(x for x in [me.first_name, me.last_name] if x) or me.username
    finally:
        await client.disconnect()


_client_locks: dict[int, asyncio.Lock] = {}


def _lock_for(user_id: int) -> asyncio.Lock:
    if user_id not in _client_locks:
        _client_locks[user_id] = asyncio.Lock()
    return _client_locks[user_id]


async def send_as_user(
    user,
    chat_id: int,
    text: str,
    photo_bytes: bytes | None = None,
) -> None:
    """Post from the client's Telegram account. Raises AccountError / FloodWaitError."""
    if not user.tg_session:
        raise AccountError("Аккаунт не привязан.")

    raw = decrypt_session(user.tg_session)
    async with _lock_for(user.id):
        client = _new_client(raw)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise AccountError("Сессия истекла. Привяжи аккаунт заново.")

            if photo_bytes:
                bio = BytesIO(photo_bytes)
                bio.name = "ad.jpg"
                await client.send_file(chat_id, bio, caption=text)
            else:
                await client.send_message(chat_id, text)
        except FloodWaitError:
            raise
        except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError) as e:
            raise AccountError(f"Нет доступа писать в эту группу: {e}") from e
        except AuthKeyError as e:
            raise AccountError("Сессия недействительна. Привяжи аккаунт заново.") from e
        finally:
            await client.disconnect()


__all__ = [
    "AccountError",
    "Need2FA",
    "api_configured",
    "encrypt_session",
    "decrypt_session",
    "normalize_phone",
    "mask_phone",
    "begin_qr_login",
    "wait_qr_login",
    "cancel_qr_login",
    "finish_password_login",
    "start_phone_login",
    "complete_phone_login",
    "verify_session",
    "send_as_user",
    "FloodWaitError",
]
