# Margó — Food cost management for Belgian restaurants

SaaS PWA that tells independent restaurateurs what each dish really costs, and alerts when margins drift. Built by Antonio (solo founder, bioengineering background, owns 3 restaurants).

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (async) + asyncpg + Alembic
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite (PWA via vite-plugin-pwa)
- **Database:** PostgreSQL 16 on Railway
- **AI:** Anthropic Claude API (Vision for OCR, text for ingredient suggestions)
- **Storage:** Cloudflare R2 (S3-compatible) for invoice images
- **Email:** Resend (transactional + inbound webhook)
- **Payments:** Stripe Billing
- **Hosting:** Railway (backend + frontend + DB)
- **Auth:** Magic link (email-only, JWT session, no passwords)

## Project structure

Monorepo with /backend and /frontend at root.

```
margo/
├── CLAUDE.md
├── backend/
│   ├── main.py                # FastAPI app entry, CORS, lifespan
│   ├── app/
│   │   ├── config.py          # pydantic-settings, env vars
│   │   ├── database.py        # async engine, sessionmaker, get_db dependency
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API route modules
│   │   └── services/          # Business logic (costing, OCR, matching, etc.)
│   ├── alembic/               # DB migrations
│   ├── tests/                 # pytest + httpx
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Route-level page components
│   │   ├── hooks/             # Custom React hooks
│   │   └── api/               # API client (fetch wrapper with JWT)
│   ├── public/
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml         # Local dev: postgres + backend + frontend
└── railway.toml
```

## Commands

- `cd backend && uvicorn main:app --reload` — run backend locally
- `cd backend && alembic upgrade head` — apply DB migrations
- `cd backend && alembic revision --autogenerate -m "description"` — create migration
- `cd backend && pytest` — run all backend tests
- `cd backend && pytest tests/test_recipes.py -v` — run specific test file
- `cd frontend && npm run dev` — run frontend locally
- `cd frontend && npm run build` — build frontend for production

## Code style

- Python: type hints everywhere, async/await, f-strings, snake_case
- Use Pydantic schemas for ALL API input/output — never return raw dicts
- SQLAlchemy models use `mapped_column()` syntax (SQLAlchemy 2.0+)
- React: functional components only, hooks, TypeScript strict
- Tailwind for all styling — no CSS files, no styled-components
- French for user-facing text (UI labels, error messages, emails)
- English for code (variable names, comments, docstrings, API endpoints)

## Data model — 5 core tables

1. **Restaurant** — id, name, owner_email, default_target_margin (default 30%)
2. **Ingredient** — id, restaurant_id (FK), name, unit (g/kg/cl/l/piece), current_price, supplier_name, last_updated
3. **Recipe** — id, restaurant_id (FK), name, selling_price, category, target_margin
4. **RecipeIngredient** — id, recipe_id (FK), ingredient_id (FK), quantity, unit
5. **Invoice** — id, restaurant_id (FK), image_url, supplier_name, invoice_date, source (email/upload/photo), format (xml/pdf/image), status (processing/pending_review/confirmed), extracted_lines (JSONB), matched_ingredients (JSONB)

Additional: **IngredientPriceHistory** — ingredient_id, price, date, invoice_id
Additional: **IngredientAlias** — alias_text, ingredient_id (learned mapping from invoice lines)

## Key business logic

- **Food cost %** = (sum of ingredient_qty × ingredient_price) / selling_price × 100
- When an ingredient price changes → recalculate ALL recipes using that ingredient
- Margin thresholds: 🟢 <30% food cost, 🟠 30-35%, 🔴 >35% (configurable per restaurant)
- Invoice matching: exact name → fuzzy (pg_trgm trigram) → suggest new ingredient
- After user confirms a match, store it as IngredientAlias for future auto-matching

## IMPORTANT rules

- NEVER store secrets in code. Use environment variables via config.py.
- ALL API endpoints require JWT auth except /auth/* and /health
- Use `get_db` dependency injection for database sessions — never create sessions manually
- Frontend API calls go through `api/client.ts` which handles JWT refresh
- Write tests for every new endpoint — use httpx AsyncClient with test DB
- Alembic migrations must be created for every model change
- French UI, English code — this is non-negotiable

## Environment variables

See `.env.example` for required vars: DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY, R2_*, RESEND_API_KEY, STRIPE_*, FRONTEND_URL, ENVIRONMENT

## Current sprint

Sprint 2 — Recipes & Food Cost. See @PLAN.md for full roadmap.
