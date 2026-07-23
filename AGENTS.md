# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python product: a **Telegram Autopost Bot** (aiogram + Telethon, SQLAlchemy async). There is no web frontend and no test suite.

### Environment
- Dependencies live in a virtualenv at `.venv/` (gitignored). Run tools with `.venv/bin/python` / `.venv/bin/pip` (or activate the venv). The startup update script creates `.venv` and runs `pip install -r requirements.txt`.
- The repo targets Python 3.11.9 (`runtime.txt`) for prod hosts, but the pinned deps also install and run fine on the system Python 3.12.
- Copy `.env.example` to `.env` for local dev. Default `DB_URL=sqlite+aiosqlite:///bot.db` is enough locally; Postgres is only needed for persistent serverless prod.

### Two run modes (same codebase)
- Polling worker (primary local path): `.venv/bin/python main.py`. Also starts the APScheduler autopost loop and supports QR login.
- Serverless webhook (FastAPI): `.venv/bin/uvicorn api.index:app --host 127.0.0.1 --port 8000`. Endpoints `GET /` and `GET /health` respond without contacting Telegram; other routes need a valid token.

### Non-obvious gotchas
- Running `main.py` requires a **real `BOT_TOKEN`** from BotFather. With a dummy/invalid token the app fully wires up and runs `init_db()` (creating `bot.db`) but then aborts at `bot.delete_webhook` with `TelegramUnauthorizedError: Unauthorized`. This is expected without the secret, not a code bug.
- `TG_API_ID` / `TG_API_HASH` (from my.telegram.org) are only needed for account linking + posting from the user's account; without them the bot logs a warning and disables those features but still starts.
- No migration tool: `init_db()` calls `Base.metadata.create_all` plus an in-code `migrate_schema` that `ADD COLUMN`s missing fields, so the schema is created/upgraded automatically on startup.
- No configured linter and no automated tests exist. For a quick syntax check use `.venv/bin/python -m compileall main.py api config.py database.py models.py handlers services middlewares utils keyboards.py states.py`.
- To exercise core business logic (users/subscriptions/ads/groups/promos/post logs) without Telegram, drive the `database.py` async CRUD functions directly with `PYTHONPATH=/workspace` — this runs the real app code end to end against SQLite.
