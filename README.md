# Telegram Autopost Bot

Бот для автопубликации объявлений в группы и барахолки: от бота (если он админ) или от аккаунта клиента (Telethon), с подпиской (Telegram Stars), админкой и чатом поддержки.

## Возможности

- Постинг **от бота** — добавь бота админом в обычную группу (удобно на Vercel)
- Постинг **от аккаунта клиента** (Telethon) — для барахолок, куда ботов не пускают
- Привязка Telegram: QR (VPS) или телефон + код (Vercel)
- Создание объявлений (текст / фото / цена)
- Выбор групп из меню Telegram
- Автопостинг с интервалом, джиттером, тихими часами и вариациями текста
- Кнопка **«Запостить сейчас»** — мгновенная отправка (важно для Vercel)
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
2. **Мои группы** → добавить барахолку/группу
   - обычная группа: добавь **бота админом** → посты от бота
   - барахолка без ботов: **Мой аккаунт → Подключить по номеру**
3. Объявление → запустить
4. Автопостинг → «Запостить сейчас» / включить + cron

> `maxDuration` в `vercel.json` = 10 сек (Hobby). На Pro можно поднять до 60 и `POST_BUDGET_SECONDS=45`.

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

## Антибан (кратко)

- интервал + jitter, тихие часы, вариации текста
- пауза между группами (на Vercel короче, чтобы уложиться в timeout)
- FloodWait → cooldown; 3 ошибки → группа отключается

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

## Планы и лимиты

| План    | Дни | Stars | Объявлений | Групп |
|---------|-----|-------|------------|-------|
| week    | 7   | 150   | 1          | 3     |
| month   | 30  | 450   | 5          | 15    |
| quarter | 90  | 1100  | 20         | 50    |
