# Telegram Autopost Bot

Бот для автопубликации объявлений в группы и барахолки: от бота (если он админ) или от аккаунта клиента (Telethon), с подпиской (Telegram Stars), админкой и чатом поддержки.

## Возможности

- Постинг **от аккаунта клиента** (Telethon) — бот в барахолки не заходит и админом не становится
- Привязка Telegram: QR (VPS) или телефон + код (Vercel)
- Создание объявлений (текст / фото / цена) с антиспам-проверкой
- Выбор групп из меню Telegram
- Автопостинг с интервалом, дневными лимитами, тихими часами и вариациями текста
- Кнопка **«Запостить сейчас»** с мягким антибан-полом
- Подписка через Telegram Stars + рефералка (+3 дня)
- Чат поддержки и админ-панель `/admin`

## Деплой на Vercel (webhook + cron)

### 1. База данных (обязательно для продакшена)

SQLite в `/tmp` на Vercel **сбрасывается**. Подключи Postgres:

1. [Neon](https://neon.tech) / Supabase / Vercel Postgres → создай БД
2. Скопируй connection string
3. В Vercel → Settings → Environment Variables:

| Key | Value |
|-----|--------|
| `BOT_TOKEN` | токен BotFather |
| `ADMIN_IDS` | твой Telegram ID |
| `DB_URL` или `POSTGRES_URL` | `postgresql://...` (нормализуется в asyncpg) |
| `TG_API_ID` | с [my.telegram.org](https://my.telegram.org) |
| `TG_API_HASH` | там же |
| `CRON_SECRET` | случайная строка |

### 2. Deploy

1. Vercel → Import GitHub repo `tgbotautopost`
2. Redeploy после добавления env
3. Открой: `https://ТВОЙ-ПРОЕКТ.vercel.app/setup-webhook` → `"ok": true`
4. Проверка: `/health` — `persistent_db: true`, `tg_api: true`
5. В Telegram: `/start`

### 3. Автопостинг по расписанию

Vercel Hobby cron — редко (в конфиге hourly; на Hobby может быть реже).  
Для реальных интервалов поставь **внешний cron** (cron-job.org / EasyCron) каждые 5–15 минут:

```
GET https://ТВОЙ-ПРОЕКТ.vercel.app/cron?secret=ТВОЙ_CRON_SECRET
```

Либо жми в боте **«Запостить сейчас»**.

### 4. Как пользоваться на Vercel

1. Подписка
2. **Мой аккаунт → Подключить по номеру** (посты только от клиента)
3. **Мои группы** → барахолки (бот в них не нужен)
4. Объявление → запустить
5. Автопостинг → «Запостить сейчас» / включить + cron

Клиент должен быть участником барахолки. Бот админом не становится.

---

## Деплой на Render (always-on, лучший автопост)

1. [render.com](https://render.com) → **New** → **Background Worker**
2. Подключи GitHub `tgbotautopost`
3. **Build:** `pip install -r requirements.txt`  
   **Start:** `python main.py`
4. Env: `BOT_TOKEN`, `ADMIN_IDS`, `DB_URL`, `TG_API_ID`, `TG_API_HASH`, `PYTHON_VERSION=3.11.9`
5. Create Worker → Live → `/start`

> Background Worker, не Web Service.  
> При старте бот сам снимает webhook (если раньше был Vercel).

Для Postgres на Render: Internal Database URL → в `DB_URL` с префиксом `postgresql+asyncpg://`.

---

## Локальный запуск

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Файл `.env` (см. `.env.example`):

```env
BOT_TOKEN=123456:ABC...
ADMIN_IDS=8414329140
DB_URL=sqlite+aiosqlite:///bot.db
TG_API_ID=12345678
TG_API_HASH=your_api_hash_here
```

```bash
python main.py
```

На `main.py` работают QR-логин и планировщик APScheduler.

## Админка

`/admin` — только ID из `ADMIN_IDS`.

## Антибан (снижение риска, не гарантия)

Посты всегда от аккаунта клиента. 100% защиты от бана в барахолке нет.

Встроено:

- минимальный интервал 60+ мин (ручной пост — мягкий пол 45 мин)
- лимит постов в сутки на группу и на пользователя
- тихие часы, джиттер, перемешивание групп
- вариации текста объявления
- проверка текста на спам-паттерны при создании
- FloodWait → длинный cooldown
- 2 ошибки / запрет писать → группа отключается + уведомление
- на Vercel: 1 группа за тик cron (безопаснее + укладывается в timeout)

Клиент сам обязан соблюдать правила каждой барахолки.

## Структура

```
config.py          # env, лимиты, IS_VERCEL
models.py          # User, Ad, TargetGroup (+ bot_can_post), …
database.py        # async SQLAlchemy CRUD
handlers/          # user, account, ads, groups, autopost, …
services/user_client.py  # Telethon
services/poster.py       # бот + user account
services/scheduler.py    # только main.py
main.py            # polling (рекомендуется для полного автопоста)
api/index.py       # Vercel webhook + /cron + /health
```

## Оплата

- **Telegram Stars** — мгновенно
- **Карта / крипта** — заявка → «Я оплатил» → админ подтверждает в боте
- Реквизиты: `PAYMENT_CARD_DETAILS`, `PAYMENT_CRYPTO_DETAILS`
- Цены ₽: `PAYMENT_RUB_WEEK` / `MONTH` / `QUARTER`

## Поддержка

Кнопка «Поддержка» → `@eb_support` (env `SUPPORT_USERNAME`) + тикет в боте.

## Планы и лимиты

| План    | Дни | Stars | ₽ (default) | Объявлений | Групп |
|---------|-----|-------|-------------|------------|-------|
| trial   | 1   | —     | —           | 1          | 2     |
| week    | 7   | 150   | 299         | 1          | 3     |
| month   | 30  | 450   | 799         | 5          | 15    |
| quarter | 90  | 1100  | 1990        | 20         | 50    |

Идеи следующих обновлений: см. `ROADMAP.md`.
