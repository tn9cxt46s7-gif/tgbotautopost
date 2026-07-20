# Telegram Autopost Bot

Бот для автопубликации объявлений в группы-барахолки с антибан-алгоритмом, подпиской (Telegram Stars), админкой и чатом поддержки.

## Возможности

- Создание объявлений на продажу (текст / фото / цена)
- Привязка групп-барахолок (бот должен быть участником)
- Автопостинг с per-group интервалом, джиттером, тихими часами и вариациями текста
- Подписка через Telegram Stars + рефералка (+3 дня)
- Чат поддержки (юзер ↔ админ)
- Админ-панель `/admin`: статистика, юзеры, подписки, объявления, группы, рассылка, тикеты

## Быстрый старт

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
```

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

1. Купи подписку (кнопка «Подписка») или получи её от админа.
2. Добавь бота в группу барахолки (с правом писать сообщения).
3. «Мои группы» → «Добавить группу» → перешли сообщение из группы.
4. «Добавить объявление» → текст → фото → цена → «Запустить».
5. «Автопостинг» → включить.

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
handlers/          # user, ads, groups, autopost, support, admin, payments
services/poster.py # антибан + отправка
services/scheduler.py
main.py            # polling entrypoint
api/index.py       # Vercel webhook (без scheduler)
```

## Планы и лимиты

| План    | Дни | Stars | Объявлений | Групп |
|---------|-----|-------|------------|-------|
| week    | 7   | 150   | 1          | 3     |
| month   | 30  | 450   | 5          | 15    |
| quarter | 90  | 1100  | 20         | 50    |
