# SnowScrape Billing MVP — Design

**Date:** 2026-05-06
**Status:** Draft for implementation
**Author:** Alex Diaz
**Sub-project of:** SnowScrape Launch Readiness (full PROGRESS.md scope)

---

## Context

SnowScrape's backend Stripe integration is mostly written but uncommitted. The frontend Settings page renders Billing and API Keys tabs against hardcoded mock data. No Stripe products exist; no webhook is registered; no Doppler vars are populated. Nothing is deployed.

This spec covers the Billing MVP only — the work needed to take the first paying user. It is sub-project #1 of a 5-part launch sequence:

| # | Sub-project | Owner | Status |
|---|---|---|---|
| 1 | **Billing MVP** | this spec | drafting |
| 2 | API Keys MVP (auth on public endpoints) | future spec | not started |
| 3 | Real analytics data pipeline | future spec | not started |
| 4 | Email notifications | future spec | not started |
| 5 | In-app notification center | future spec | not started |

Sub-projects #2-5 are out of scope here. They will get their own brainstorm → spec → plan cycles after this one ships.

## Goals

- Take the first revenue dollar.
- Trial-only entry: 14-day trial of Pro, card required upfront.
- Stripe Customer Portal handles all self-service plan changes.
- Webhook handler is idempotent and retry-safe.
- Settings page Billing and API Keys tabs read real data.

## Non-goals

- Annual pricing (deferred; backend env-var slots get removed)
- Email or in-app notifications, including `trial_will_end` reminders
- Real analytics page wiring (mocks stay until sub-project #3)
- API-key authentication on `/jobs` etc. (sub-project #2 — keys are created but Clerk JWT remains the only accepted auth)
- Usage-based / metered billing
- Promotional codes / coupons
- Tax handling beyond Stripe automatic tax
- Hard-deleting revoked API keys (soft-delete only; revoked rows persist with `is_active=false`)
- Existing-user migration (Subscriptions table is empty)

---

## Prerequisites (resolve before implementation starts)

1. **Webhook endpoint domain.** The current SST config produces an auto-generated API Gateway URL (e.g. `https://<id>.execute-api.us-east-2.amazonaws.com/`). The Stripe webhook URL must be stable across redeploys. Two options:
   - **Option A (recommended for MVP):** register the auto-generated URL once per stage; update Stripe's webhook URL on the rare event that the API Gateway is recreated. Acceptable for v1 since teardowns are deliberate.
   - **Option B:** add a custom domain to `sst.aws.ApiGatewayV2` (e.g. `api-dev.snowscrape.snowforge.dev` / `api.snowscrape.snowforge.dev`) before provisioning the webhook. Adds a Route 53 record + ACM certificate to the SST config.

   Pick one before provisioning Stripe. Spec assumes Option A unless the implementation plan switches to B.

2. **Email address for Enterprise "Contact us" link.** Pricing page placeholder is `alex@snowforge.dev`. Confirm or replace before merging the pricing page change.

3. **Frontend Stripe publishable key.** Not needed — Stripe Checkout is fully redirect-based, so no `@stripe/stripe-js` integration is required. Listing here so it doesn't get added inadvertently.

4. **CORS origins per stage.** The existing `corsOrigins` map in `sst.config.ts` must include the production domain (e.g. `https://snowscrape.snowforge.dev`) before the prd deploy. Verify at deploy time.

## Architectural decisions

### 1. Subscription state machine & data model

**`PLAN_LIMITS` revision.** Drop `starter`. Replace with `locked` (the lockout sentinel: `monthly_pages: 0`, all features `False`). The shipped tiers are:

| Plan | Monthly price | Pages/month | Concurrent jobs | js_rendering | proxy_rotation | webhooks | anti_bot |
|---|---|---|---|---|---|---|---|
| `pro` | $49 | 25,000 | 5 | ✓ | ✓ | ✓ | ✗ |
| `business` | $149 | 100,000 | 20 | ✓ | ✓ | ✓ | ✓ |
| `enterprise` | Custom (sales-led) | unlimited (-1) | unlimited (-1) | ✓ | ✓ | ✓ | ✓ |
| `locked` | n/a | 0 | 0 | ✗ | ✗ | ✗ | ✗ |

`pro` is the only plan reachable through Stripe Checkout. `business` is reachable only through plan-change in the Customer Portal (avoids a parallel Business-trial codepath). `enterprise` is provisioned manually by writing the row directly in DynamoDB.

**Status as gate, not metadata.** Add `is_subscription_active(sub) -> bool` that returns `True` for `trialing` and `active`, `False` for `past_due`, `canceled`, `incomplete`, `incomplete_expired`, `unpaid`, and the synthetic `no_subscription`. Every billing-enforcement function (`check_usage_quota`, `check_concurrent_job_limit`, `check_feature_access`) consults this guard and returns `allowed: False` with an explicit reason when inactive.

**`_default_subscription` sentinel.** Returns `{plan: "locked", status: "no_subscription"}` instead of auto-granting starter. The first persisted Subscriptions row is created when `checkout.session.completed` fires.

**`Subscriptions` table additions** (no migration; table is empty):
- `trial_end` — ISO timestamp from `Subscription.trial_end`. Surfaced in Billing tab for the "Trial ends in N days" banner.
- `cancel_at_period_end` — bool from `Subscription.cancel_at_period_end`. Surfaced for "Resubscribe" CTA.

**Fail-open vs fail-closed.** Quota checks at job-creation are fail-closed (DB error → 500, do not allow). `increment_usage` after a job finishes is fail-open (logs error, never re-raises) — usage drift is acceptable; blocking job completion is not.

### 2. Signup → checkout flow & post-trial UX

**Mandatory chokepoint.** Clerk signup completes → Next.js middleware checks `GET /billing/subscription` (60s cookie cache to avoid hot-pathing the Lambda) → if status is not `trialing` or `active`, redirect:
- `no_subscription` → `/onboarding/checkout`
- `past_due`, `incomplete` → `/billing/locked?reason=payment_failed`
- `canceled` → `/billing/locked?reason=canceled`

**`/onboarding/checkout` page.** Friction-free landing copy ("Start your 14-day Pro trial — card required, cancel anytime") and one CTA. Click triggers `POST /billing/checkout` with `{plan: "pro", is_trial: true}`, then 302 to the returned `checkout_url`.

**`/billing/locked` page.** Full-screen banner with one CTA: "Manage subscription" → `POST /billing/portal` → 302 to Stripe Customer Portal. From the portal the user can update card or resubscribe.

**Backend `create_checkout_session_handler` change.** Accept an `is_trial` body flag (default true on `/onboarding/checkout`, false on portal-driven plan changes). When `is_trial` is true, pass `subscription_data={"trial_period_days": 14}` and `payment_method_collection="always"` to `Session.create`.

**No data deletion at trial/sub end.** Jobs and results stay in DynamoDB / S3 until the existing 365-day S3 lifecycle hits. A returning user who fixes billing finds their work intact.

**Read-only carve-out for locked users.** Allow `GET /jobs`, `GET /jobs/{id}`, `GET /results/{id}`, `GET /templates`, and `GET /webhooks` so users can export their data after lockout. Implemented as a `read_only_when_locked` decorator on the explicit allowlist. Everything else returns `402 Payment Required` with `{message, plan, status}` body.

### 3. Settings page wiring (Billing + API Keys tabs)

**Billing tab.** Replace all hardcoded mock content. Two TanStack Query hooks:
- `useSubscription()` → `GET /billing/subscription`, 60s stale time. Returns `{plan, status, current_period_end, monthly_page_limit, monthly_pages_used, trial_end, cancel_at_period_end, has_billing_account, features}`.
- `useUsage()` → `GET /billing/usage`, 30s stale time.

Tab content:
- **Plan card** — `plan` + `status` badge (Trialing → blue, Active → green, Past Due → red, Canceled → gray). When `status === "trialing"`, banner shows "Trial ends in N days" computed from `trial_end`. Buttons: "Manage subscription" and "Upgrade to Business" both → `POST /billing/portal`. Stripe Customer Portal handles the actual plan change.
- **Usage card** — progress bar `pages_used / pages_limit` with `pages_percentage`. Color thresholds: <80% neutral, 80-95% amber, >95% red. Sub-text: `Resets on {billing_period_end}`. No CTA when over limit (API is already 402'ing).
- **Payment Method card and Billing History card — deleted.** Stripe Customer Portal renders these natively.

**API Keys tab.** Replace mock array with real fetches:
- `useApiKeys()` → `GET /api-keys`
- `createApiKey({name})` → `POST /api-keys`
- `deleteApiKey(id)` → `DELETE /api-keys/{api_key_id}` (soft delete; row stays with `is_active=false`)

**One-time-secret modal (new).** Click "Create API Key" → Dialog asks for a name (max 100 chars). On submit, the modal switches to a key-display state showing:
1. The full `sk_live_...` key in a read-only Input with a Copy button
2. A warning banner: "Save this now — it won't be shown again"
3. A required checkbox "I've saved this key" that gates the Close button

After close, the raw key leaves React state. The list shows only `key_prefix` (`sk_live_xxxx`) for stored keys with no reveal option. The existing show-hide eye toggle and full-key reveal Input on stored keys are removed (the keys are SHA-256 hashed at rest; the raw value is unrecoverable).

The `Active` badge becomes `Active`/`Revoked` based on `is_active`. Revoked keys appear at the bottom in muted styling.

### 4. Pricing page revisions & plan-change UX

**Pricing page surgery (`/pricing`):**
- Delete the Starter card. Replace with hero copy above the grid: "Start with a 14-day free trial of Pro. No charge until day 15. Cancel anytime."
- Pro card primary CTA → "Start 14-day trial".
- Business card secondary CTA → "Start with Pro, upgrade anytime".
- Enterprise card → "Contact us" mailto link to **alex@snowforge.dev** (placeholder — confirm at provisioning time before merging the page change).
- Feature comparison table: remove the Starter column.

**`<PricingCTA />` client component routing:**
- Signed-out → Clerk modal sign-up → existing `afterSignUpUrl` lands on `/dashboard` → middleware redirects to `/onboarding/checkout`.
- Signed-in with `status in {trialing, active}` → `POST /billing/portal` → portal.
- Signed-in with no subscription → `/onboarding/checkout`.

**Plan changes — delegated to Stripe Customer Portal.** No in-app plan picker. Configure the portal once via dashboard to enable plan switching between Pro/Business prices, cancellation at period end, payment method updates, invoice download. Promo codes off for MVP.

**Downgrade semantics.**
- Stripe prorates difference and credits next invoice automatically.
- `_handle_subscription_updated` already pulls the new tier from `items[0].price.metadata.tier` and writes the new limit.
- **`monthly_pages_used` is NOT reset on plan change.** A user who scraped 30k on Business and downgrades to Pro mid-period stays at 30k used / 25k limit (i.e. quota'd out for the remainder). Prevents the "downgrade to dodge the cap" exploit. Reset happens at the next `current_period_end`.
- **Bug fix in `_handle_subscription_updated`:** today it sets `usage_reset_date = current_period_end` on every update. That erroneously shifts the reset date when a user changes payment method without a period rollover. Guard: only update `usage_reset_date` if the new value differs from the stored value.

**Cancel flow.** Portal cancel → Stripe sets `cancel_at_period_end=true` → backend writes `cancel_at_period_end=true` to DynamoDB. App stays fully usable until period end. At period end, `customer.subscription.deleted` fires → backend sets `plan="locked"`, `status="canceled"` (changed from current code's "downgrade to starter"). User hits locked screen on next request and can resubscribe via portal.

### 5. Webhook hardening (idempotency + retries)

**`BillingWebhookDedup` table** (new):
- Hash key: `event_id` (Stripe event ID, e.g. `evt_1ABC...`)
- TTL on `ttl` attribute: 30 days
- PITR + SSE on by default

**Restructured `stripe_webhook_handler`:**
1. Verify signature → 400 on failure (no DynamoDB call yet).
2. Conditional put `{event_id, ttl, type}` with `ConditionExpression="attribute_not_exists(event_id)"`.
   - On `ConditionalCheckFailedException` → log "duplicate ignored" → return 200 immediately.
3. Dispatch handler for `event_type`.
4. On dispatch success → return 200.
5. On dispatch exception → delete the dedup row (best-effort) → return 500 so Stripe retries.

This replaces the current "always-200 after sig verification" pattern, which silently loses events on transient failures.

**Race fix in `_handle_subscription_updated`:** read current `usage_reset_date` first; only write if it differs from `subscription.current_period_end`. Prevents double-resets when `subscription.updated` and `invoice.payment_succeeded` arrive close together at period boundary.

**Subscribed events (5):** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.

**Not subscribed (deferred):** `customer.subscription.trial_will_end` — needs email infra (sub-project #4). Frontend "Trial ends in N days" banner is sufficient for launch.

### 6. Operations, testing, scope boundary

#### 6.1 Stripe provisioning (one-time, per stage)

Run twice — once in **test mode** (used by `dev` stage), once in **live mode** (used by `prod` stage).

1. Log in to the SnowForge LLC Stripe account.
2. Create products: "SnowScrape Pro" and "SnowScrape Business". Set each product's `metadata.tier` to `pro` / `business` (the backend's `_plan_from_subscription` reads this).
3. Create monthly recurring prices: $49/mo (Pro), $149/mo (Business), USD. Capture the `price_...` IDs.
4. Configure Customer Portal: enable plan switching between the two prices, enable cancel-at-period-end, enable payment method updates, enable invoice history + download. Promo codes off.
5. Create a webhook endpoint at the URL determined by Prerequisites #1 (auto-generated API Gateway URL or custom domain), path `/billing/webhook`. Subscribe to the 5 events listed in section 5. Capture the `whsec_...` signing secret.

#### 6.2 Doppler env layout

`sf-snowscrape` project, `dev` and `prd` configs. Each holds:

```
STRIPE_SECRET_KEY            # sk_test_... in dev, sk_live_... in prd
STRIPE_WEBHOOK_SECRET        # whsec_... — different per stage
STRIPE_PRICE_PRO_MONTHLY     # price_... — different per stage
STRIPE_PRICE_BUSINESS_MONTHLY # price_... — different per stage
```

**Removed from `sst.config.ts` `sharedEnv`** (unused under monthly-only, no-starter model):
- `STRIPE_PRICE_STARTER_MONTHLY`
- `STRIPE_PRICE_PRO_ANNUAL`
- `STRIPE_PRICE_BUSINESS_ANNUAL`

#### 6.3 Deploy sequencing

Strict order; do not interleave:
1. Populate Doppler `dev` with all 4 vars.
2. `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`. Confirm `Subscriptions`, `ApiKeys`, `BillingWebhookDedup` tables exist and Lambdas link them. Confirm webhook endpoint URL matches what was registered in Stripe.
3. Smoke test backend (see 6.4).
4. Wire frontend → deploy to Vercel preview → click through trial flow with Stripe test card `4242 4242 4242 4242`.
5. Repeat 1-4 for `prd` with live keys. Final smoke test: a real $49 charge against your own card, refunded, with webhook confirmed delivered cleanly through the BillingWebhookDedup table.

#### 6.4 Smoke test checklist (run after each stage deploy)

- [ ] New user signup → middleware redirects to `/onboarding/checkout`.
- [ ] Stripe checkout completes → returns to `/dashboard?checkout=success` → Subscriptions row exists with `status=trialing`, `trial_end` populated.
- [ ] Create a job → succeeds within trial.
- [ ] Settings → Billing → real plan, real usage, "Trial ends in N days" banner.
- [ ] Stripe dashboard "Advance test clock" past trial → `invoice.payment_succeeded` lands → status flips to `active`, `monthly_pages_used` reset to 0.
- [ ] Create API key → modal shows raw key once → list view shows masked prefix only.
- [ ] Cancel subscription via portal → `cancel_at_period_end=true` written → app still usable.
- [ ] Decline a test card to trigger `past_due` → next request → locked screen.
- [ ] Replay a webhook event from Stripe dashboard twice → log shows "duplicate ignored", subscription row unchanged.

#### 6.5 Test strategy

- **Unit (Python, pytest + moto):** `billing.py` — quota math, feature gates, default sentinel, status guard. `billing_handler.py` — split each `_handle_*` function for individual test access; mock `stripe.Subscription.retrieve`. Target ≥80% on both files.
- **Integration (Python, pytest + moto):** Full webhook flow with recorded Stripe payloads (via `stripe-cli` fixtures). Idempotency test: submit same event twice, assert dispatch ran exactly once.
- **Frontend (Vitest):** `useSubscription`, `useUsage`, `useApiKeys` hooks (mock fetch).
- **Frontend (Playwright):** `/onboarding/checkout` redirect, `/billing/locked` redirect, create-API-key modal one-time-secret flow.
- **Manual:** Stripe Checkout itself — hosted page, not E2E-tested. The smoke checklist covers it.

#### 6.6 Rollback plan

- **Bad code deploy:** `npx sst deploy --stage <stage>` against the previous git SHA reverts in <5 min.
- **Live trials already in flight:** Stripe holds those subscriptions independently; rolling back code does not cancel them. Webhook endpoint must remain reachable through any rollback.
- **Destructive table removal (only if needed):** SST will not auto-delete tables that contain data. Manual `aws dynamodb delete-table` against `snowscrape-{stage}-Subscriptions`, `-ApiKeys`, `-BillingWebhookDedup`. Document this in the implementation plan; do not run blindly.

---

## Change summary by file

### Backend
- `backend/billing.py` — drop `starter`, add `locked`, add `is_subscription_active`, change `_default_subscription` to return sentinel, add `trial_end` and `cancel_at_period_end` to `create_or_update_subscription`.
- `backend/billing_handler.py` — restructure `stripe_webhook_handler` for idempotency, fix `_handle_subscription_updated` reset-date race, change `_handle_subscription_deleted` to set `locked` instead of `starter`, accept `is_trial` flag in `create_checkout_session_handler` to pass `trial_period_days`, populate `trial_end` and `cancel_at_period_end` in `_handle_checkout_completed` and `_handle_subscription_updated`.
- `backend/handler.py` — extend the existing billing-enforcement block at job creation to consult `is_subscription_active`. Add `read_only_when_locked` decorator and apply to the GET allowlist.

### Infra
- `sst.config.ts` — add `BillingWebhookDedup` table, remove unused `STRIPE_PRICE_STARTER_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL`, `STRIPE_PRICE_BUSINESS_ANNUAL` from `sharedEnv`.
- `sst.pyi` / `backend/sst.pyi` — regenerated automatically by SST; expect a `BillingWebhookDedup` class.

### Frontend
- `frontend/middleware.ts` — add subscription-status gate after Clerk auth.
- `frontend/app/(application)/onboarding/checkout/page.tsx` — new.
- `frontend/app/(application)/billing/locked/page.tsx` — new.
- `frontend/app/(application)/dashboard/settings/page.tsx` — wire Billing tab to real hooks; replace API Keys mock with real hooks; rebuild create-API-key modal as one-time-secret flow; delete Payment Method card and Billing History card.
- `frontend/app/(marketing)/pricing/page.tsx` — drop Starter card, update copy, wire `<PricingCTA />`.
- `frontend/lib/api/billing.ts` — new (TanStack Query hooks for `useSubscription`, `useUsage`).
- `frontend/lib/api/api-keys.ts` — new (`useApiKeys`, `createApiKey`, `deleteApiKey`).

### Docs
- `docs/INFRASTRUCTURE.md` — add `Subscriptions`, `ApiKeys`, `BillingWebhookDedup` tables, document the trial-only flow, update env-var section.
- `PROGRESS.md` — mark Billing MVP done; revise the "What's NOT DONE" list.
- `backend/openapi.yml` — add the 5 billing routes and 3 api-key routes.

---

## Risks

- **Stripe Customer Portal config drift between dev and prd.** The portal config lives in Stripe's dashboard, not in code. Easy to forget to mirror a setting (e.g. enabling cancellation) in the prd account. Mitigation: keep a checklist screenshot of each setting in `docs/INFRASTRUCTURE.md`.
- **Middleware Lambda hot-path on every request.** Mitigated by 60s cookie cache. If page-load latency degrades, the cache lifetime can extend without code change.
- **Webhook lag during cold starts.** A 30s Stripe timeout combined with a 20-second Lambda cold start could push past the deadline, causing Stripe to retry. The new idempotency table handles this safely.
- **No staging smoke between dev and prd.** Skipping a real-money smoke in `prd` is the highest-risk shortcut; the smoke checklist explicitly requires the $49-then-refund test before declaring `prd` shipped.
