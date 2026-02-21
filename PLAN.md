# Margó — Development Plan

8 sprints, 8 weeks. Each sprint = 1 week with a testable deliverable.

## Sprint 1 — Foundations (Week 1)
**Goal:** App deployed, auth works, CRUD ingredients

- [ ] SQLAlchemy models for all 5 core tables + Alembic initial migration
- [ ] FastAPI app with CORS, health check, lifespan events
- [ ] Auth: POST /auth/login (send magic link) → POST /auth/verify (verify token, return JWT)
- [ ] JWT middleware: decode token, inject current user into request
- [ ] CRUD /api/ingredients (GET list with search, GET by id, POST, PUT, DELETE)
- [ ] React app: Vite + TypeScript + Tailwind + react-router + PWA manifest
- [ ] Frontend: Login page (email input → magic link sent → verify callback)
- [ ] Frontend: Ingredients page (list + add/edit modal)
- [ ] API client (api/client.ts) with JWT header injection
- [ ] Tests: auth flow + ingredients CRUD (pytest + httpx)
- [ ] Deploy to Railway (backend + frontend + DB)

**Deliverable:** Live app at heymargo.be, can log in and manage ingredients.

## Sprint 2 — Recipes & Food Cost (Week 2)
**Goal:** Calculator works, dashboard shows margins

- [ ] CRUD /api/recipes with nested ingredients [{ingredient_id, quantity, unit}]
- [ ] Service costing.py: calculate food cost per recipe (sum qty × price / selling_price)
- [ ] GET /api/dashboard: food cost moyen, recipes sorted by food cost %, thresholds
- [ ] Cascade recalculation when ingredient price changes
- [ ] Frontend: Recipe list + detail page with ingredient picker (autocomplete)
- [ ] Frontend: Real-time food cost calculation on recipe edit (client-side)
- [ ] Frontend: Dashboard V1 — avg food cost, dishes sorted green/orange/red
- [ ] Tests: recipe CRUD, food cost calculation, cascade update

**Deliverable:** Encode 10-15 real dishes from Le Moulin Simonis. See real food costs.

## Sprint 3 — AI Onboarding (Week 3)
**Goal:** Photo of menu → all dishes with suggested ingredients in 20 minutes

- [ ] Cloudflare R2 integration (upload service with presigned URLs)
- [ ] POST /api/onboarding/extract-menu: image → Claude Vision → [{dish, price, category}]
- [ ] POST /api/onboarding/suggest-ingredients: dishes → Claude text → [{ingredient, qty, unit}] per dish
- [ ] POST /api/onboarding/confirm: batch create ingredients + recipes in one transaction
- [ ] Frontend: Onboarding flow — step 1: photo/upload menu, step 2: review dishes, step 3: review ingredients per dish, step 4: confirm all
- [ ] Tests: mock Claude API, test extraction + suggestion + batch creation

**Deliverable:** Photograph Le Roy de la Moule menu, get full dashboard in 20 min.

## Sprint 4 — Invoice Import: XML/PDF (Week 4)
**Goal:** E-invoices parsed automatically, prices update

- [ ] Parser UBL/Peppol XML (lxml): extract supplier, date, lines, totals
- [ ] Parser PDF (pdfplumber): extract text, attempt structured parsing
- [ ] POST /api/invoices/upload: accept XML/PDF/image, detect format, route to parser
- [ ] Matching service: exact match → fuzzy (pg_trgm) → suggest new. IngredientAlias table.
- [ ] POST /api/invoices/{id}/confirm: update prices, save aliases, trigger cascade recalc
- [ ] Frontend: Import page with drag & drop zone + file type detection
- [ ] Frontend: Invoice review screen (extracted lines + match suggestions + confirm)
- [ ] Tests: parser XML (2-3 real UBL files), parser PDF, matching logic, cascade

**Deliverable:** Import 3-4 real invoices from Le Moulin Simonis. Prices update automatically.

## Sprint 5 — OCR Photo + Email Forward (Week 5)
**Goal:** All 3 import channels operational

- [ ] OCR service: image → Claude Vision → structured JSON (same schema as XML/PDF parsers)
- [ ] Email inbound: configure Resend/Mailgun webhook for factures@heymargo.be
- [ ] Webhook endpoint: receive email → extract attachment → detect format → parse
- [ ] Unified invoice router: any input format → standardized InvoiceExtraction
- [ ] IngredientPriceHistory table + populated on every confirmed invoice
- [ ] GET /api/ingredients/{id}/price-history
- [ ] Frontend: Invoice list page (date, supplier, status, source badge)
- [ ] Frontend: Notification badge "1 new invoice to review"
- [ ] Tests: OCR pipeline, email webhook, price history

**Deliverable:** Forward a real invoice email → appears in app → review → prices update.

## Sprint 6 — Alerts + Simulator (Week 6)
**Goal:** Product feature-complete. Start beta.

- [ ] Alert system: after invoice confirm, check if any recipe crossed threshold → create alert
- [ ] Alert email template: "⚠️ [ingredient] +X%. Impacted dishes: [list with before/after]"
- [ ] POST /api/recipes/{id}/simulate: {new_selling_price?, ingredient_adjustments?} → before/after comparison + monthly impact estimate
- [ ] GET /api/alerts (list, mark as read)
- [ ] Frontend: Simulator page — price slider + portion sliders, real-time recalc (client-side), before/after display, monthly savings estimate, "Apply changes" button
- [ ] Frontend: Dashboard V2 — alert banner, link to simulator from red/orange dishes
- [ ] Frontend: Price history chart (recharts line chart on ingredient detail)
- [ ] Tests: alert generation, simulator calculations

**Deliverable:** Feature-complete product. Onboard 5-10 beta restaurants from network.

## Sprint 7 — Polish & Beta Fixes (Week 7)
**Goal:** Stable for production use

- [ ] Fix bugs from beta testers (prioritize by impact)
- [ ] Mobile UX polish (real device testing, camera PWA, touch targets)
- [ ] Improve matching with real-world invoice data from beta
- [ ] Sentry integration (error tracking)
- [ ] Performance: check N+1 queries, add DB indexes if needed
- [ ] PWA offline: cache dashboard for offline viewing

**Deliverable:** Stable app ready for paying customers.

## Sprint 8 — Monetization & Launch (Week 8)
**Goal:** Stripe billing, landing page, public launch

- [ ] Stripe Billing: Free (5 recipes, 3 invoices/mo) + Pro €14.90/mo + Multi €24.90/mo
- [ ] Middleware: enforce plan limits on relevant endpoints
- [ ] Frontend: Pricing page + upgrade flow + Stripe customer portal
- [ ] Landing page (public, SEO-optimized, "food cost restaurant belgique")
- [ ] Export CSV: GET /api/export/invoices?from=&to= (for accountants)
- [ ] Multi-restaurant: switch context, consolidated dashboard for Multi plan
- [ ] Tests: billing enforcement, export

**Deliverable:** 🎉 Public launch. First paying customers.
