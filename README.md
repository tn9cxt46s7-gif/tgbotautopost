# Telegram Autopost Bot

Бот для автопубликации объявлений в группы-барахолки с антибан-алгоритмом, подпиской (Telegram Stars), админкой и чатом поддержки.

## Возможности

- Постинг **от аккаунта клиента** (Telethon) — бота в барахолки добавлять не нужно
- Привязка Telegram: телефон → код → 2FA
- Создание объявлений на продажу (текст / фото / цена)
- Выбор групп из меню Telegram
- Автопостинг с per-group интервалом, джиттером, тихими часами и вариациями текста
- Подписка через Telegram Stars + рефералка (+3 дня)
- Чат поддержки (юзер ↔ админ)
- Админ-панель `/admin`: статистика, юзеры, подписки, объявления, группы, рассылка, тикеты

## Деплой на Vercel (бесплатно, с ограничениями)

Бот **может отвечать** на кнопки через webhook. Автопостинг на бесплатном Vercel слабый (база в `/tmp` сбрасывается, cron раз в сутки).

1. Vercel → Import GitHub repo `tgbotautopost`
2. **Settings → Environment Variables** добавь:

| Key | Value |
|-----|--------|
| `BOT_TOKEN` | токен BotFather |
| `ADMIN_IDS` | твой Telegram ID |

3. Redeploy (Deployments → Redeploy)
4. Открой в браузере: `https://ТВОЙ-ПРОЕКТ.vercel.app/setup-webhook`
5. Должно показать `"ok": true`
6. В Telegram напиши боту `/start`

Если не отвечает — открой `/setup-webhook` ещё раз и проверь, что `BOT_TOKEN` точно в Environment Variables (Production).


1. Зайди на [render.com](https://render.com) → **New** → **Background Worker**
2. Подключи GitHub-репозиторий `tgbotautopost`
3. Настройки:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. **Environment** (Environment Variables):

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | токен от BotFather |
| `ADMIN_IDS` | твой Telegram ID |
| `DB_URL` | `sqlite+aiosqlite:///bot.db` |
| `PYTHON_VERSION` | `3.11.9` |

5. **Create Worker** → дождись статуса **Live**
6. Напиши боту `/start`

> Важно: выбирай **Background Worker**, не Web Service.  
> Web Service на Render ждёт HTTP-порт — для polling-бота это ломает деплой.

Если раньше ставил webhook на Vercel — не страшно: при старте бот сам снимает webhook.

### База данных

SQLite на бесплатном Render может сброситься при редеплое.  
Для серьёзной работы: **New → PostgreSQL** в Render, скопируй Internal Database URL и в `DB_URL` поставь:

```
postgresql+asyncpg://user:pass@host/dbname
```

(замени `postgres://` в начале на `postgresql+asyncpg://`)


```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

Создай файл `.env`:

```env
BOT_TOKEN=123456:ABC...
ADMIN_IDS=8414329140
DB_URL=sqlite+aiosqlite:///bot.db
TG_API_ID=12345678
TG_API_HASH=your_api_hash_here
```

`TG_API_ID` / `TG_API_HASH` возьми на [my.telegram.org](https://my.telegram.org) → API development tools.  
Без них привязка аккаунта и автопостинг не работают.

Для PostgreSQL:

```env
DB_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

Запуск (polling + планировщик автопостинга):

```bash
python main.py
```

> Автопостинг работает только при always-on процессе (`main.py`).  
> Vercel webhook (`api/index.py`) принимает апдейты, но не держит APScheduler.

## Как пользоваться

1. Купи подписку («Подписка») или получи от админа.
2. **«Мой аккаунт» → Привязать** → телефон → код из Telegram (и 2FA, если есть).
3. «Мои группы» → добавить барахолки из меню (бота туда **не** добавляем).
4. «Добавить объявление» → текст → фото → цена → «Запустить».
5. «Автопостинг» → включить.

> Автопостинг и привязка аккаунта стабильно работают через `python main.py` (always-on).  
> На Vercel webhook меню отвечает, но планировщик и Telethon-логин там ненадёжны.

## Админка

Команда `/admin` (только ID из `ADMIN_IDS`).

## Антибан (кратко)

На каждую группу:

- минимальный интервал + случайный jitter
- тихие часы (UTC)
- вариации текста объявления
- пауза 30–120 сек между группами
- FloodWait → cooldown
- 3 ошибки подряд → группа отключается + уведомление юзеру

## Структура

```
config.py          # env, лимиты планов
models.py          # User, Ad, TargetGroup, Payment, PostLog, SupportTicket
database.py        # async SQLAlchemy CRUD
keyboards.py       # reply/inline + premium emoji
states.py          # FSM
utils/emoji.py     # именованные premium emoji
utils/subscription.py
handlers/          # user, account, ads, groups, autopost, support, admin, payments
services/user_client.py  # Telethon: логин + пост от аккаунта
services/poster.py # антибан + отправка через user session
services/scheduler.py
main.py            # polling entrypoint (рекомендуется)
api/index.py       # Vercel webhook (без надёжного автопостинга)
```

## Планы и лимиты

| План    | Дни | Stars | Объявлений | Групп |
|---------|-----|-------|------------|-------|
| week    | 7   | 150   | 1          | 3     |
| month   | 30  | 450   | 5          | 15    |
| quarter | 90  | 1100  | 20         | 50    |
