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
        raise AccountError(
            "Админ ещё не настроил TG_API_ID / TG_API_HASH (my.telegram.org)."
        )
    return TelegramClient(StringSession(session), TG_API_ID, TG_API_HASH)


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
    Finish login. Returns (raw_session_string, display_name).
    Raises Need2FA if cloud password is required (with updated pending session).
    """
    phone = normalize_phone(phone)
    code = (code or "").strip().replace(" ", "")
    client = _new_client(pending_session)
    await client.connect()
    try:
        try:
            if password is not None:
                await client.sign_in(password=password)
            else:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError as e:
            raise Need2FA(client.session.save()) from e
        except PhoneCodeInvalidError as e:
            raise AccountError("Неверный код. Попробуй ещё раз.") from e
        except PhoneCodeExpiredError as e:
            raise AccountError("Код устарел. Начни привязку заново.") from e

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
    "start_phone_login",
    "complete_phone_login",
    "verify_session",
    "send_as_user",
    "FloodWaitError",
]
