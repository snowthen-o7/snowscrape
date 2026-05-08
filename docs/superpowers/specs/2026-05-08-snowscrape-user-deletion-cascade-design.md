# SnowScrape User Deletion Cascade — Design

**Date:** 2026-05-08
**Status:** Draft for implementation
**Author:** Alex Diaz
**Sub-project of:** SnowScrape Launch Readiness — billing-related compliance

---

## Context

Today, when a SnowScrape user deletes their Clerk account (via the `<UserButton>` in the dashboard), only the Clerk auth identity is removed. **Everything in SnowScrape's databases stays orphaned**, including their active Stripe subscription. The user assumes "delete = gone", but Stripe will keep charging them at the next renewal.

Concrete consequences of the current state:

- **Stripe subscription continues to bill.** Trial converts to paid charge after day 15; renewals continue indefinitely until the card declines.
- **Subscriptions row** stays in DynamoDB forever, indexed by a Clerk user_id that no longer resolves.
- **API keys remain `is_active=true`.** When sub-project #2 wires `Authorization: Bearer sk_live_...` middleware on `/jobs`, anyone with a previously-issued raw key for the deleted user can still hit the API.
- **Jobs / Templates / Webhooks / WebhookDeliveries / Urls** rows persist with no clear ownership.
- **S3 results** stay until the existing 365-day lifecycle hits.

This is a refund-liability and trust problem. Solving it requires listening for Clerk's `user.deleted` webhook and cascading the cleanup.

## Goals

- When a Clerk user is deleted, immediately cancel their Stripe subscription so no further charges occur.
- Hard-delete the user's rows from all SnowScrape DynamoDB tables.
- Soft-delete (archive in place) S3 result data; rely on the existing lifecycle for hard deletion.
- Idempotent processing — Clerk retries webhooks; the handler must tolerate duplicate `user.deleted` events.
- Add a friction step in the UI so users understand what "delete account" means before they click.

## Non-goals

- Pro-rated refunds. Stripe's `subscription.cancel(...)` with default proration handles credit semantics; we do not push a manual refund. If the user paid for a full month and deletes on day 5, the subscription cancels with the period credit applied to a future invoice (which never comes since they're gone).
- Trash/restore UI. Deletes are immediate and final. A restore concept would require GDPR-style data export, out of scope.
- Mass-delete cron for users who became Clerk-orphaned before this lands. A one-time backfill script can be run separately if needed; not part of this MVP.
- GDPR Article 17 right-to-erasure paperwork. The handler covers the data-deletion mechanic; legal documentation is a separate compliance line.

---

## Architectural decisions

### 1. Webhook source: Clerk Svix-verified

Clerk emits webhooks via Svix. Each event includes a signed payload + signature header (`svix-signature`, `svix-id`, `svix-timestamp`). Verification uses the `svix` Python SDK with a stage-specific secret.

**New Doppler vars** (`sf-snowscrape/dev` and `sf-snowscrape/prd`):
- `CLERK_WEBHOOK_SECRET` — `whsec_...` from Clerk dashboard's webhook configuration

The webhook URL is registered once per stage in the Clerk dashboard:
- dev: `https://g5vmashyda.execute-api.us-east-2.amazonaws.com/clerk/webhook`
- prd: `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com/clerk/webhook`

Subscribed events (minimum): `user.deleted`. Optional future additions: `user.created` (for analytics), `session.created` (login tracking).

### 2. New Lambda handler

**File:** `backend/clerk_webhook_handler.py`

**Route:** `POST /clerk/webhook`

**Handler:** `handle_clerk_webhook(event, context)`

Flow (mirroring the Stripe webhook idempotency pattern from `billing_handler.py`):

1. Verify Svix signature using `CLERK_WEBHOOK_SECRET`. On failure → 400.
2. Conditional-put the event ID on `BillingWebhookDedup` (we reuse it; rename internally to `WebhookDedup` is optional cleanup, see "Future renaming" below). On duplicate → 200 immediately.
3. Switch on `event.type`:
   - `user.deleted` → `_handle_user_deleted(data)`
   - else → log "unhandled" → 200 (no-op for events we don't subscribe to)
4. On dispatch exception → roll back dedup row → 500 so Clerk retries.

### 3. `_handle_user_deleted` cascade order

The order matters because Stripe cancellation can fail (network) and we want billing-stop to run first; if it fails, we 500 and Clerk retries the whole thing safely.

```
def _handle_user_deleted(payload):
    user_id = payload["id"]  # Clerk uses "id" for user.deleted

    # 1. Cancel Stripe subscription (most important — stops billing)
    sub = get_subscription(user_id)
    stripe_sub_id = sub.get("stripe_subscription_id")
    if stripe_sub_id:
        try:
            stripe.Subscription.cancel(stripe_sub_id)  # immediate, not at_period_end
        except stripe.InvalidRequestError as e:
            # Already canceled — fine, swallow
            if "No such subscription" not in str(e):
                raise

    # 2. Delete from each user-keyed DynamoDB table
    _delete_subscriptions_row(user_id)
    _delete_api_keys_for_user(user_id)
    _delete_jobs_for_user(user_id)
    _delete_templates_for_user(user_id)
    _delete_webhooks_for_user(user_id)
    _delete_webhook_deliveries_for_user(user_id)
    _delete_urls_for_user(user_id)
    # NOTE: Sessions table is connection-state ephemera (TTL'd) — skip.
    # NOTE: S3 results: NOT touched here. Rely on 365-day lifecycle.

    logger.info("User cascade-delete complete", user_id=user_id)
```

### 4. Deletion is hard-delete

We do not soft-delete. A deleted user's data is gone, period. Rationale:
- Soft-delete leaves rows with stale ownership metadata that's a discoverability hazard.
- We have no UX for restoring deleted accounts.
- Storage cost from accumulated soft-deleted rows is real but small; the bigger cost is reasoning overhead.

API keys are an exception in spirit: `delete_api_keys_for_user` performs an actual `delete_item`, NOT a flip to `is_active=false`. The active soft-delete pattern (used by `delete_api_key_handler` for end-user revoke) preserves the key row for audit trail. Cascade delete is account-termination — no audit trail to preserve for someone who no longer exists.

### 5. S3 results — deferred to lifecycle

S3 result objects are **not** deleted by the cascade. The existing 365-day Glacier-then-delete lifecycle handles eventual cleanup. Rationale:

- S3 deletes are paginated and slow at scale; risks Lambda timeout.
- Object keys aren't trivially mappable to user_id without a Jobs scan to enumerate job_ids first. By the time we delete the Jobs rows, we lose that mapping.
- A 365-day hold for a deleted user's results is acceptable (no auth identity left to access them; the bucket is private).

If GDPR or a customer specifically requests faster deletion, we add a `cleanup_orphan_results_handler` cron that scans S3 for objects whose `job_id` no longer exists in the Jobs table. Out of scope for MVP.

### 6. Pagination on the multi-row deletes

Each `_delete_*_for_user` helper queries via the appropriate GSI and deletes via `BatchWriteItem` in chunks of 25 (DynamoDB limit). For most users this is one batch. Worst case (heavy users with thousands of jobs) could hit Lambda timeout — set the function's timeout to **60 seconds** and accept that pathological cases retry via Clerk's webhook retry.

### 7. Idempotency boundary

Reusing `BillingWebhookDedup` is fine. The `event_id` namespace doesn't collide between Stripe (`evt_xxx`) and Clerk (`msg_xxx` Svix IDs). If we ever want a stricter separation, rename the table to `WebhookDedup` in a migration — but that's cosmetic.

A subtler concern: if the cascade is partially complete and then fails, the dedup row is rolled back (per the Stripe pattern), and Clerk retries — which means the partially-deleted state gets re-delete'd. Each `_delete_*_for_user` helper must be idempotent (no error if rows are already gone). DynamoDB's `delete_item` is naturally idempotent. `stripe.Subscription.cancel` raises if already canceled — handle it (see step 1 above).

### 8. UI changes — warn before delete

Clerk's `<UserButton>` ships with a default "Delete account" menu item that's one click away. We need a friction step.

Two options:

**A. Override the menu item** (preferred): replace Clerk's default delete with a custom item that opens our own modal. The modal explains:
> Deleting your account will:
> • Cancel your subscription immediately (you won't be charged again)
> • Permanently delete your scrape jobs, results, and API keys
> • Cannot be undone
>
> [Cancel] [Yes, delete my account]

Clerk's `<UserButton.MenuItems>` accepts custom action items. Confirm via modal → call Clerk's `clerk.user.delete()` from the client.

**B. Disable Clerk's default delete entirely**: configure `<ClerkProvider>` with `appearance` to hide the menu, force users into our modal-only flow. Higher friction but unambiguous.

Option A is the launch choice. Option B is overkill.

---

## Data-flow diagram

```
User clicks "Delete account" in <UserButton>
  ↓
Custom modal explains consequences → user confirms
  ↓
Frontend calls clerk.user.delete()
  ↓
Clerk deletes auth identity
  ↓
Clerk emits user.deleted webhook → POST /clerk/webhook
  ↓
backend/clerk_webhook_handler.handle_clerk_webhook
  ├── verify Svix signature → 400 on fail
  ├── conditional-put on BillingWebhookDedup → 200 if duplicate
  ├── _handle_user_deleted(data):
  │     ├── stripe.Subscription.cancel (immediate)
  │     ├── DELETE from Subscriptions
  │     ├── DELETE from ApiKeys (via UserIdIndex GSI, batch)
  │     ├── DELETE from Jobs (scan + filter, batch)
  │     ├── DELETE from Templates
  │     ├── DELETE from Webhooks
  │     ├── DELETE from WebhookDeliveries
  │     └── DELETE from Urls
  ├── return 200 on success
  └── on exception: rollback dedup row + 500 (Clerk retries)
```

---

## Change summary by file

### Backend
- **Create** `backend/clerk_webhook_handler.py` — webhook receiver + cascade logic.
- **Create** `backend/tests/unit/test_clerk_webhook.py` — signature verification, idempotency, partial-failure rollback, no-op on unhandled events.
- **Create** `backend/tests/integration/test_user_deletion_cascade.py` — full cascade against moto-mocked DynamoDB, mocked stripe.Subscription.cancel.
- **Modify** `backend/billing.py` — no changes.
- **Modify** `backend/billing_handler.py` — no changes (we reuse `BillingWebhookDedup` table without changes).

### Infra
- **Modify** `sst.config.ts` — add `POST /clerk/webhook` route, add `CLERK_WEBHOOK_SECRET` to `sharedEnv`. Lambda timeout 60s.

### Frontend
- **Modify** `frontend/components/layout/SnowScrapeLayout.tsx` — replace Clerk's default delete menu item with a `<DeleteAccountModal />` trigger.
- **Create** `frontend/components/billing/DeleteAccountModal.tsx` — confirmation modal explaining cascade consequences.

### Docs
- **Modify** `docs/INFRASTRUCTURE.md` — document the new webhook endpoint, Clerk webhook env var, cascade order.
- **Modify** `PROGRESS.md` — track this as a Billing-MVP follow-up.

---

## Operational checklist

### One-time setup per stage

1. In Clerk dashboard → Webhooks → Add endpoint:
   - URL: stage-specific webhook URL (see Architecture §1)
   - Subscribed events: `user.deleted`
   - Capture the `whsec_...` signing secret.
2. Add `CLERK_WEBHOOK_SECRET` to Doppler `sf-snowscrape/{dev,prd}` with the secret from step 1.
3. Deploy: `doppler run --project sf-snowscrape --config <stage> -- npx sst deploy --stage <stage>`.
4. Verify the route is reachable: `curl -X POST <api-url>/clerk/webhook` should return 400 (missing signature) — confirms the route exists and is signature-protected.

### Smoke test (per stage)

1. Sign up a fresh test user (frontend → Clerk → checkout → trialing subscription).
2. Verify Subscriptions row exists.
3. Click delete account → confirm in modal → modal triggers Clerk's delete.
4. Watch:
   - DynamoDB Subscriptions table: row gone within ~5s.
   - Stripe dashboard: subscription status `canceled`.
   - DynamoDB BillingWebhookDedup: new row with the Clerk event ID.
5. Re-trigger the same Clerk event from the Clerk dashboard's "Replay" button → confirm 200 with no second cascade (idempotency).

---

## Risks

- **Clerk delete UX bypass.** A user who doesn't go through our modal (e.g. by directly calling Clerk's API or using the Clerk dashboard if they have access) still triggers the webhook → cascade still runs. The modal is friction, not a gate. This is fine.
- **Stripe customer record retained.** `subscription.cancel` doesn't delete the customer object on Stripe's side. Stripe customer records are cheap and useful for audit/analytics. We don't delete them.
- **Race with in-flight job processing.** A user who deletes during an active job: the job's `process_job_handler` is already running, may write a new Subscriptions row update via `increment_usage`. The cascade wins eventually (next webhook delivery from Clerk is final), but a brief window may leave stale data. Acceptable for MVP — affected user is gone anyway.
- **Webhook delivery failure.** Clerk retries failed webhook deliveries with exponential backoff for ~24 hours. If our endpoint stays down longer, the cascade is permanently dropped. Mitigation: CloudWatch alarm on Lambda errors for the webhook handler — already covered by the existing `snowscrape-{stage}-lambda-errors` alarm wired in `sst.config.ts`.
- **API-key cascade vs. compromised keys.** A user might want to "delete one specific API key" without deleting their whole account. That's already supported by `delete_api_key_handler`. Cascade is for whole-account termination only.

---

## Future improvements (not in this MVP)

- **Pro-rated refund** for the unused portion of the current period if the user paid mid-period (uncommon for trial-only users).
- **GDPR export** before deletion: email the user a JSON dump of their data first.
- **Cascade for organization deletion** if SnowScrape ever supports orgs.
- **Rename `BillingWebhookDedup` → `WebhookDedup`** to match its expanded scope. Pure cosmetic; defer.
- **Archive S3 results to a `deleted-users/` prefix** with a separate, shorter lifecycle (30 days instead of 365). Implement when there's a real product reason (e.g. compliance request).
