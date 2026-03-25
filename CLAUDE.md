# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Tabienrod Backend — a FastAPI application that monitors Thailand's DLT vehicle registration plate reservation schedule and notifies subscribers by email when their desired number becomes available.

## Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install dependencies |
| `uv run uvicorn app.main:app --reload` | Local development |
| `uv run alembic upgrade head` | Run database migrations |
| `uv run alembic revision --autogenerate -m "description"` | Generate new migration |
| `uv run python scripts/run_cron.py` | Run cron job manually |

**No test suite exists yet.**

## Architecture

**Runtime**: Python 3.12+ with FastAPI, managed by `uv`.

**Entrypoint**: `app/main.py` — FastAPI app with lifespan.

**Request flow**: FastAPI router in `app/routes.py` (prefix `/api`) handles:
- `POST /api/subscribe` — register email + vehicle_type + desired_number, sends confirmation email
- `GET /api/confirm/{token}` — confirm subscription (24h expiry)
- `GET /api/unsubscribe/{token}` — delete subscription

**Cron flow** (`app/cron.py`): Fetches DLT page → extracts Google Drive PDF link → downloads PDF → parses Thai-language schedule → matches against confirmed subscribers → sends notification emails. Run via `scripts/run_cron.py` with system cron.

**Key modules**:
- `app/scraper.py` — DLT page fetching (httpx), Google Drive link extraction, PDF text parsing with Thai date conversion
- `app/email_service.py` — Mailgun email sending (httpx), loads HTML templates from `templates/` at runtime
- `app/schemas.py` — Pydantic models with validation (vehicle types: `รย.1`, `รย.2`, `รย.3`)
- `app/constants.py` — Vehicle type ↔ Thai letter series mapping
- `app/config.py` — pydantic-settings, loads from `.env`
- `app/database.py` — Async SQLAlchemy engine + session factory
- `app/models.py` — SQLModel table definitions

**Database**: PostgreSQL via SQLModel (async with asyncpg). Migrations managed by Alembic. Tables: `subscribers`, `schedules`, `notifications`, `cron_runs`.

**Environment variables** (in `.env`):
- `PG_CONN_STRING` — PostgreSQL connection string
- `MAILGUN_API_KEY` — Mailgun API key
- `MAILGUN_DOMAIN` — Mailgun sending domain
- `BASE_URL` — Public URL for confirmation/unsubscribe links

## Important Patterns

- Database sessions are injected via FastAPI `Depends(get_session)`
- Settings are injected via `Depends(get_settings)` or imported directly from `app.config`
- HTTP calls use `httpx.AsyncClient`
- Email templates are HTML files in `templates/`, read at runtime and cached
- All user-facing text is in Thai
