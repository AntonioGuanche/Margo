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
│   │   ├── dependencies.py    # get_current_restaurant + get_admin from JWT
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── routers/           # API route modules
│   │   │   ├── auth.py        # magic link login/verify
│   │   │   ├── ingredients.py # CRUD + auto-categorization backfill
│   │   │   ├── recipes.py     # CRUD + food cost calculation + DELETE /all
│   │   │   ├── invoices.py    # upload, review, confirm, portion calc
│   │   │   ├── onboarding.py  # AI menu extraction + batch creation
│   │   │   ├── admin.py       # founder admin: stats, users, plan editing, normalize
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
│   ├── tests/                 # pytest + httpx (154 tests)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # Reusable UI (Skeleton, UpgradeModal, ConfirmModal, Layout, Nav, MenuUploadZone)
│   │   ├── pages/
│   │   │   ├── Recipes.tsx    # "Ma carte" — inline upload zone + drag&drop + manual add + delete individual/all
│   │   │   ├── RecipeDetail.tsx
│   │   │   ├── Ingredients.tsx
│   │   │   ├── Onboarding.tsx # 4-step: upload menu → review dishes → review ingredients → done
│   │   │   ├── InvoiceUpload.tsx
│   │   │   ├── InvoiceReview.tsx # line matching + recipe creation + portions
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Admin.tsx      # founder admin page: stats + user table + plan editing
│   │   ├── types/             # Shared TS types (mirror of Pydantic schemas)
│   │   │   ├── index.ts       # Re-export all
│   │   │   ├── ingredient.ts  # Ingredient, UnitType, IngredientListResponse…
│   │   │   ├── recipe.ts      # RecipeListItem, RecipeDetail, DashboardResponse…
│   │   │   ├── invoice.ts     # InvoiceListItem, LineState, InvoiceConfirmLine…
│   │   │   ├── alert.ts       # AlertItem, AlertListResponse
│   │   │   ├── restaurant.ts  # RestaurantInfo, RestaurantList
│   │   │   ├── simulator.ts   # SimulateResponse, SimulationState
│   │   │   └── admin.ts       # AdminStats, AdminUser, NormalizeUnitsResponse
│   │   ├── hooks/
│   │   │   ├── useRecipes.ts  # CRUD + useDeleteRecipe + useDeleteAllRecipes
│   │   │   ├── useIngredients.ts
│   │   │   ├── useInvoices.ts  # includes portion/volume fields
│   │   │   ├── useOnboarding.ts # useExtractMenu, useSuggestIngredients, useConfirmOnboarding
│   │   │   ├── useBilling.ts
│   │   │   └── useAdmin.ts    # useAdminCheck, useAdminStats, useAdminUsers, useUpdateUserPlan, useNormalizeUnits
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
- `cd backend && pytest` — run all backend tests (154 tests, ~15min on remote DB)
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

- **Food cost %** = (sum of convert_quantity(qty, recipe_unit, ingredient_unit) × ingredient_price) / selling_price × 100
- **Unit normalization:** `ingredient.unit` is ALWAYS a base unit: `kg`, `l`, or `piece`. Prices are always €/kg, €/l, or €/piece. `normalize_to_base_unit()` in costing.py auto-converts g→kg, cl→l, ml→l at all entry points (ingredient create/update, invoice confirm, onboarding). Chef uses any unit in recipes (g, cl...); `convert_quantity()` handles the math.
- **Unit conversion:** `convert_quantity()` in costing.py handles g↔kg, ml↔cl↔l, piece/pce via `UNIT_TO_BASE` dict. Falls back to no conversion if units are incompatible or unknown.
- When an ingredient price changes → recalculate ALL recipes using that ingredient
- Margin thresholds: 🟢 <30% food cost, 🟠 30-35%, 🔴 >35% (configurable per restaurant)
- Invoice matching: exact name → fuzzy (pg_trgm trigram) → suggest new ingredient
- **Multi-recipe per invoice line:** each line can be linked to multiple recipes via `recipe_links` array (RecipeLink schema with `recipe_id`, `quantity`, `unit`). No legacy single-recipe fields.
- After user confirms a match, store it as IngredientAlias for future auto-matching
- **Invoice portions:** unit_parser.py parses Belgian packaging patterns (24/3, CASIER 24, 6x25cl), calculates volume-based portions for beer/wine/spirit with interactive serving size
- **Onboarding:** photo/PDF of menu → AI extracts dishes (with cocktail category) → AI suggests ingredients (homemade only) → purchased items auto-get ingredient = product name (qty 1, unit piece) → batch creation
- **Cocktail detection:** `is_cocktail()` in utils.py + `isCocktail()` in Onboarding.tsx detect cocktails by name/keywords → marked homemade (has sub-ingredients). Non-cocktail boissons → purchased.
- **Plan limits:** free = unlimited (temporarily, revert to 5 recipes / 3 invoices/month after field testing). Pro/Multi = unlimited.

## Important patterns

- **`_line_dict_to_response()`** in invoices.py eliminates duplication across upload/get/patch response building, computes portion fields on-read
- **Transparent backfill:** auto-categorize ingredients with no category on GET /ingredients (via `guess_ingredient_category`)
- **`unit_parser.py`** fallback: if OCR doesn't extract `units_per_package`, regex parses it from description (4-48 range sanity check)
- **Onboarding navigate state:** Recipes.tsx → `/onboarding` with `{ dishes, skipExtract }` (pre-extracted) or `{ file }` (auto-extract)
- **Delete recipes:** Individual delete via Trash2 hover button + ConfirmModal. "Supprimer tout le menu" with SUPPRIMER text confirmation. Backend DELETE /all route placed before /{recipe_id} to avoid path collision.
- **Delete invoices:** Trash2 hover button on ALL invoices (including confirmed) in Invoices.tsx + ConfirmModal. Backend DELETE /{invoice_id} allows deleting any invoice.
- **Ingredient chips:** InvoiceReview.tsx shows assigned ingredients as orange chips (with match score % and X button) instead of dropdown. "Changer" button reveals dropdown override. Create mode shows green "Sera créé" badge.
- **RecipeLinker:** Chip-based multi-recipe component in InvoiceReview. Auto-fetches existing recipe links via GET `/api/ingredients/{id}/recipes` and pre-fills chips. Users can add/remove recipes, adjust quantity/unit per chip.
- **MenuUploadZone:** Shared component (components/MenuUploadZone.tsx) used in Dashboard empty state and Recipes page. Supports drag&drop, multi-file sequential extraction with progress, camera, optional manual add button.
- **€ symbol:** Price input in StepDishes uses absolute-positioned € suffix (not in placeholder)
- **Shared types:** `frontend/src/types/` directory with 8 files mirroring Pydantic schemas (ingredient.ts, recipe.ts, invoice.ts, alert.ts, restaurant.ts, simulator.ts, admin.ts, index.ts). All hooks import from `types/`, re-export key types for backward compatibility. Pages import types from `../types` directly. Convention: `*Response` for API responses, `*Request` for requests, `*State` for frontend state.
- **Admin access:** `ADMIN_EMAILS` env var (comma-separated). `get_admin` dependency in `dependencies.py` checks `restaurant.owner_email` against admin list. Frontend uses `GET /admin/check` (useAdminCheck hook) to conditionally show admin sidebar link (Shield icon). Admin router at `/admin` prefix with 5 endpoints: check, stats, users, update plan, normalize-units per restaurant.
- **DB Reset:** `POST /api/restaurants/reset` bulk-deletes all data for authenticated restaurant. Delete order: aliases → price_history → recipes (cascade recipe_ingredients) → ingredients → invoices. Explicit alias delete and price_history delete needed because bulk `delete()` bypasses ORM cascade and `IngredientPriceHistory.invoice_id` has no `ondelete`. Settings.tsx "Zone de danger" section with RÉINITIALISER text confirmation. Redirects to dashboard after reset.

## IMPORTANT rules

- NEVER store secrets in code. Use environment variables via config.py.
- ALL API endpoints require JWT auth except /auth/* and /health
- Use `get_db` dependency injection for database sessions — never create sessions manually
- Frontend API calls go through `api/client.ts` which handles JWT refresh
- Write tests for every new endpoint — use httpx AsyncClient with test DB
- Alembic migrations must be created for every model change
- French UI, English code — this is non-negotiable

## Workflow après chaque sprint ("comme d'hab")

1. Faire un **résumé** clair de l'action réalisée
2. Lancer les tests (`pytest`), le type-check (`npx tsc --noEmit`) et le build (`npm run build`) avant de commit
3. **Commit** (message en français) + **push**
4. **Git archive** sur le Bureau : `git archive -o "/c/Users/Utilisateur/Desktop/margo.zip" HEAD`
5. **Mettre à jour CLAUDE.md** (section "Current sprint" + nouveaux patterns/changements)

## Environment variables

See `.env.example` for required vars: DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY, R2_*, RESEND_API_KEY, STRIPE_*, FRONTEND_URL, ENVIRONMENT, ADMIN_EMAILS

## Domain

- **Domain:** heymargo.be
- **Inbound email:** factures@heymargo.be (or factures+{restaurant_id}@heymargo.be)
- **App URL:** https://heymargo.be (production)

## Current sprint

Sprint 40 — Suppression cascade d'ingrédients. DELETE /ingredients/{id} supprime maintenant les recipe_ingredient links et recalcule le food cost des recettes affectées (au lieu de retourner 409). Migration Alembic `e1f2a3b4c5d6` : ondelete=CASCADE sur recipe_ingredients.ingredient_id. Message confirmation frontend mis à jour. Tests mis à jour (test_delete_ingredient_with_recipes + edge cases).

### Sprint history
Previous: Sprint 39 (volume lines €/l en frontend), Sprint 38 (onboarding confirm crash + proxy vite + utcnow + invoice delete FK-safe), Sprint 37 (reset DB depuis Paramètres + retrait fix-inflated-prices), Sprint 36 (fix-inflated-prices + sidebar sticky), Sprint 35 (admin panel + query limit 500), Sprint 34 (normalisation unités — migration avec sur-inflation), Sprint 33 (P4 types partagés), Sprint 32 (P3 fiabilité), Sprint 31 (P2 navigation), Sprint 30 (hardening P0+P1), Sprint 29b (unit sync on confirm), Sprint 29 (unit conversion), Sprint 28b (batch recipe pre-fill), Sprint 28 (autoSuggested reset), Sprint 27 (re-confirm/patch/delete confirmed invoices), Sprint 26 (RecipeLinker chip component), Sprint 25 (ingredient chips). See @PLAN.md for original roadmap.
