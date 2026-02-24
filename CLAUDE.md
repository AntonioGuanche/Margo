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

Monorepo with /backend and /frontend at root. Multi-stage Dockerfile (Node + Python). `scripts/start.sh` runs Alembic migrations (sync psycopg2) then launches uvicorn.

```
margo/
├── CLAUDE.md
├── PLAN.md
├── backend/
│   ├── main.py                # FastAPI app entry, CORS, lifespan
│   ├── app/
│   │   ├── config.py          # pydantic-settings, env vars
│   │   ├── database.py        # async engine, sessionmaker, get_db dependency
│   │   ├── dependencies.py    # get_current_restaurant from JWT
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API route modules
│   │   │   ├── auth.py        # magic link login/verify
│   │   │   ├── ingredients.py # CRUD + auto-categorization backfill
│   │   │   ├── recipes.py     # CRUD + food cost calculation
│   │   │   ├── invoices.py    # upload, review, confirm, portion calc
│   │   │   ├── onboarding.py  # AI menu extraction + batch creation
│   │   │   ├── billing.py     # Stripe checkout, portal, plan info
│   │   │   ├── dashboard.py   # KPIs + alerts
│   │   │   └── simulator.py   # what-if price changes
│   │   ├── services/
│   │   │   ├── costing.py     # food cost calculation
│   │   │   ├── ocr.py         # Claude Vision invoice OCR
│   │   │   ├── matching.py    # fuzzy ingredient matching (pg_trgm)
│   │   │   ├── billing.py     # Stripe + PLAN_LIMITS
│   │   │   ├── unit_parser.py # parse_units_per_package, parse_volume_liters, SERVING_SIZES
│   │   │   ├── utils.py       # guess_ingredient_category (Belgian keywords)
│   │   │   ├── onboarding_ai.py # Claude menu extraction + ingredient suggestion
│   │   │   ├── email_inbound.py # Resend webhook for factures@heymargo.be
│   │   │   └── storage.py     # R2 upload with presigned URLs
│   │   └── middleware/
│   │       ├── plan_limits.py # require_recipe_quota, require_invoice_quota
│   │       └── rate_limit.py  # AI + upload rate limiting
│   ├── alembic/               # DB migrations
│   ├── scripts/start.sh       # Alembic upgrade + uvicorn launch
│   ├── tests/                 # pytest + httpx (123 tests)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI (Skeleton, UpgradeModal, Layout, Nav)
│   │   ├── pages/
│   │   │   ├── Recipes.tsx    # "Ma carte" — inline upload zone + drag&drop + manual add
│   │   │   ├── RecipeDetail.tsx
│   │   │   ├── Ingredients.tsx
│   │   │   ├── Onboarding.tsx # 4-step: upload menu → review dishes → review ingredients → done
│   │   │   ├── InvoiceUpload.tsx
│   │   │   ├── InvoiceReview.tsx # line matching + recipe creation + portions
│   │   │   ├── Dashboard.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   ├── useRecipes.ts
│   │   │   ├── useIngredients.ts
│   │   │   ├── useInvoices.ts  # includes portion/volume fields
│   │   │   ├── useOnboarding.ts # useExtractMenu, useSuggestIngredients, useConfirmOnboarding
│   │   │   └── useBilling.ts
│   │   └── api/
│   │       └── client.ts      # fetch wrapper with JWT header injection
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
- `cd backend && pytest` — run all backend tests (123 tests, ~15min on remote DB)
- `cd backend && pytest tests/test_recipes.py -v` — run specific test file
- `cd frontend && npm run dev` — run frontend locally
- `cd frontend && npm run build` — build frontend for production
- `cd frontend && npx tsc --noEmit` — TypeScript type check

## Code style

- Python: type hints everywhere, async/await, f-strings, snake_case
- Use Pydantic schemas for ALL API input/output — never return raw dicts
- SQLAlchemy models use `mapped_column()` syntax (SQLAlchemy 2.0+)
- React: functional components only, hooks, TypeScript strict
- Tailwind for all styling — no CSS files, no styled-components
- French for user-facing text (UI labels, error messages, emails)
- English for code (variable names, comments, docstrings, API endpoints)

## Data model — core tables

1. **Restaurant** — id, name, owner_email, plan (free/pro/multi), default_target_margin (30%), stripe_customer_id, stripe_subscription_id
2. **Ingredient** — id, restaurant_id (FK), name, unit (g/kg/cl/l/piece), current_price, supplier_name, category (auto-guessed), last_updated
3. **Recipe** — id, restaurant_id (FK), name, selling_price, category, is_homemade, target_margin, food_cost, food_cost_percent
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
- **Invoice portions:** unit_parser.py parses Belgian packaging patterns (24/3, CASIER 24, 6x25cl), calculates volume-based portions for beer/wine/spirit with interactive serving size
- **Onboarding:** photo/PDF of menu → AI extracts dishes (with cocktail category) → AI suggests ingredients (homemade only) → purchased items auto-get ingredient = product name (qty 1, unit piece) → batch creation
- **Cocktail detection:** `is_cocktail()` in utils.py + `isCocktail()` in Onboarding.tsx detect cocktails by name/keywords → marked homemade (has sub-ingredients). Non-cocktail boissons → purchased.
- **Plan limits:** free = 200 recipes (temporarily raised from 5), 3 invoices/month. Pro/Multi = unlimited.

## Important patterns

- **`_line_dict_to_response()`** in invoices.py eliminates duplication across upload/get/patch response building, computes portion fields on-read
- **Transparent backfill:** auto-categorize ingredients with no category on GET /ingredients (via `guess_ingredient_category`)
- **`unit_parser.py`** fallback: if OCR doesn't extract `units_per_package`, regex parses it from description (4-48 range sanity check)
- **Onboarding navigate state:** Recipes.tsx → `/onboarding` with `{ dishes, skipExtract }` (pre-extracted) or `{ file }` (auto-extract)

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

## Domain

- **Domain:** heymargo.be
- **Inbound email:** factures@heymargo.be (or factures+{restaurant_id}@heymargo.be)
- **App URL:** https://heymargo.be (production)

## Current sprint

Sprint 20 — Cocktails = homemade by default. See @PLAN.md for original roadmap.
