# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run dev server (port 8000, Swagger at /docs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

No test suite or linter config exists yet.

## Architecture

### Layering

Routes (`app/api/`) → Schemas (`app/schemas/`) → Models (`app/models/`) → Services (`app/services/`) → DB

- **Routes** inject `db: Session = Depends(get_db)` and call `ProductService` static methods for complex logic; simpler routes query the ORM directly.
- **Schemas** follow the `Base → Create / Update / Response` pattern. All use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.
- **Models** use UUID PKs, PostgreSQL `JSONB` for flexible attributes (`ProductCatalog.attributes`), and self-referential FK for category hierarchy (`Category.parent_id`).
- **Services** (`ProductService`) use raw SQL via `text()` for performance-sensitive or complex queries (fuzzy match, upserts). Prefer this pattern over ORM for joins and aggregates.

### Data Model

```
Manufacturer → Brand → ProductCatalog  (master product)
                              ↓
                         Product (one per store)
                              ↓
                           Price  →  price_history (DB trigger)
Store ────────────────────────↑
```

`ProductCatalog` is the deduplicated reference product. `Product` is the per-retailer instance. `Price` is 1:1 with `Product`; history is appended automatically by a DB trigger.

### Key Behaviors

- **Fuzzy search** relies on `pg_trgm` (`similarity() > 0.3`). The extension must exist in the database.
- **`GET /api/brands/search`** hits the external Google Shopping scraper and can auto-create `ProductCatalog` entries when `create_products=true`. Category is inferred via keyword mapping in `detect_category_from_name()`.
- **Store upsert**: `get_store_by_name_or_create()` auto-creates missing stores as inactive.
- **Database URL**: `database.py` rewrites `postgresql://` → `postgresql+psycopg://` at startup to force psycopg3.
- **`ProductCatalog.attributes`** (JSONB) stores scraper metadata: `jumbo_id`, `jumbo_url`, `jumbo_price`, `source`.

## Environment

Copy `.env.example` to `.env`. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL (psycopg3 driver) |
| `ALLOWED_ORIGINS` | CORS — defaults to localhost:5173/5174 |
| `SECRET_KEY` / `ALGORITHM` | JWT (not yet wired) |
| `REDIS_URL` / `CELERY_*` | Task queue (not yet wired) |
| `AWS_*` / `S3_BUCKET_NAME` | S3 export (not yet wired) |

## What's Not Implemented

- JWT authentication (env vars exist, no middleware)
- Celery tasks (dependency installed, no task definitions)
- Alembic migrations (directory exists, not initialized)
- AWS S3 export
