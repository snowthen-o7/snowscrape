# SnowScrape Infrastructure

**Last Updated:** 2026-06-02
**AWS Account ID:** 282128795857
**Primary Region:** us-east-2
**Production Frontend:** https://scrape.snowforge.dev (Vercel project `snowscrape`)
**Production API:** https://2pg2gj4048.execute-api.us-east-2.amazonaws.com

---

## Architecture Overview

SnowScrape is a serverless web scraping platform deployed on AWS.

```
[Vercel] ──HTTPS──> [API Gateway] ──> [Lambda Functions]
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
              [DynamoDB]              [SQS Queues]            [S3 Bucket]
              (14 tables)          (3 queues + 3 DLQs)       (results)
```

**Frontend:** Next.js on Vercel (region: iad1)
**Backend:** 29 AWS Lambda functions via SST Ion (TypeScript IaC, Pulumi engine)
**Auth:** Clerk JWT tokens (keys stored in SSM Parameter Store)

---

## AWS Resources

### Lambda Functions (29 total)

| Function | Handler | Memory | Timeout | Purpose |
|----------|---------|--------|---------|---------|
| healthCheck | handler.health_check_handler | 256 MB | 10s | Health monitoring |
| createJob | handler.create_job_handler | 512 MB | 30s | Create scraping job |
| getJobs | handler.get_jobs_handler | 512 MB | 30s | List user jobs |
| getJob | handler.get_job_handler | 512 MB | 30s | Get job details |
| updateJob | handler.update_job_handler | 512 MB | 30s | Update job config |
| deleteJob | handler.delete_job_handler | 512 MB | 30s | Delete job |
| pauseJob | handler.pause_job_handler | 512 MB | 30s | Pause/resume job |
| cancelJob | handler.cancel_job_handler | 512 MB | 30s | Cancel running job |
| refreshJob | handler.refresh_job_handler | 512 MB | 30s | Refresh job URLs |
| jobProcessor | handler.process_job_handler | 1024 MB | 900s | Execute scraping |
| scheduleJobs | handler.schedule_jobs_handler | 512 MB | 60s | 5-min scheduler |
| getCrawls | handler.get_crawl_handler | 512 MB | 30s | Get crawl history |
| *...templates* | handler.*_template_handler | 512 MB | 30s | Template CRUD (4) |
| *...webhooks* | handler.*_webhook_handler | 512 MB | 30s | Webhook CRUD (5) |
| webhookDelivery | webhook_delivery_handler | 512 MB | 60s | SQS webhook sender |
| *...utilities* | handler.* | 256-512 MB | 30s | Validation, preview |

### DynamoDB Tables (14)

| Table | Partition Key | Sort Key | GSIs | Encryption | PITR | TTL |
|-------|--------------|----------|------|------------|------|-----|
| Jobs | job_id (S) | - | StatusIndex (status), ScheduleIndex (jobStatus + nextRun) | SSE | Enabled | - |
| Urls | job_id (S) | url (S) | StatusIndex (status) | SSE | Enabled | - |
| Sessions | job_id (S) | - | - | SSE | Enabled | - |
| Templates | template_id (S) | - | UserIdIndex (user_id) | SSE | Enabled | - |
| Webhooks | webhook_id (S) | - | UserIdIndex (user_id) | SSE | Enabled | - |
| WebhookDeliveries | delivery_id (S) | - | WebhookIdIndex (webhook_id + timestamp) | SSE | Enabled | - |
| ProxyPool | proxy_id (S) | - | - | SSE | Enabled | - |
| Connections | connection_id (S) | - | - | SSE | - | `ttl` (WebSocket) |
| Subscriptions | user_id (S) | - | StripeCustomerIndex (stripe_customer_id) | SSE | Enabled | - |
| ApiKeys | api_key_id (S) | - | UserIdIndex (user_id), KeyHashIndex (key_hash) | SSE | Enabled | `ttl` (reserved) |
| BillingWebhookDedup | event_id (S) | - | - | SSE | Enabled | `ttl` (30 days) |
| GoogleAccounts | user_id (S) | - | GoogleUserIdIndex (google_user_id) | SSE + KMS | Enabled | - |
| ExportDestinations | destination_id (S) | - | UserIdIndex (user_id) | SSE | Enabled | - |
| DocsExports | export_id (S) | - | JobIdIndex (job_id), UserIdIndex (user_id) | SSE | Enabled | `ttl` (90 days) |

All tables use PAY_PER_REQUEST billing mode.

#### Subscriptions Table

- **Resource name:** `Subscriptions` (SST resource), `snowscrape-{stage}-Subscriptions`
- **Partition key:** `user_id` (string)
- **GSI:** `StripeCustomerIndex` on `stripe_customer_id` (string), full projection — used for reverse-lookups during Stripe webhook handling
- **Encryption:** SSE (AES-256)
- **PITR:** Enabled
- **TTL:** Not used (subscriptions are long-lived records)
- **Purpose:** Stores per-user subscription state — plan tier (`pro`/`business`/`enterprise`/`locked`), Stripe customer/subscription/price IDs, status (`trialing`/`active`/`past_due`/`canceled`), `trial_end`, `cancel_at_period_end`, monthly page usage counters, and billing period boundaries.

#### ApiKeys Table

- **Resource name:** `ApiKeys`, `snowscrape-{stage}-ApiKeys`
- **Partition key:** `api_key_id` (string, UUID)
- **GSIs:**
  - `UserIdIndex` on `user_id` (full projection) — lists all keys for a user
  - `KeyHashIndex` on `key_hash` (full projection) — fast lookup at API authentication time
- **Encryption:** SSE
- **PITR:** Enabled
- **TTL:** Enabled on `ttl` attribute (reserved for future ephemeral keys; not currently set)
- **Purpose:** Stores user-generated API keys. The raw key is hashed (SHA-256) before storage; only the hash and a short human-readable prefix are persisted. Soft-delete via `is_active=false`.

#### BillingWebhookDedup Table

- **Resource name:** `BillingWebhookDedup`, `snowscrape-{stage}-BillingWebhookDedup`
- **Partition key:** `event_id` (string, Stripe event ID e.g. `evt_xxx`)
- **No GSIs**
- **Encryption:** SSE
- **PITR:** Enabled
- **TTL:** Enabled on `ttl` attribute — 30-day retention window
- **Purpose:** Idempotency table for the Stripe webhook handler. A conditional-put on `event_id` ensures each Stripe event is processed exactly once, even when Stripe retries delivery.

#### GoogleAccounts Table

- **Resource name:** `GoogleAccounts`, `snowscrape-{stage}-GoogleAccounts`
- **Partition key:** `user_id` (string)
- **GSI:** `GoogleUserIdIndex` on `google_user_id` (string, full projection) — used to find user by Google account ID during OAuth callback
- **Encryption:** SSE + KMS (refresh tokens encrypted with alias/snowscrape-{stage}-oauth-tokens)
- **PITR:** Enabled
- **TTL:** Not used
- **Purpose:** Per-user Google OAuth account record. Stores `access_token_expires_at`, KMS-encrypted refresh token, and OAuth scope list. Access tokens are not persisted — refreshed on-demand per-export.

#### ExportDestinations Table

- **Resource name:** `ExportDestinations`, `snowscrape-{stage}-ExportDestinations`
- **Partition key:** `destination_id` (string, UUID)
- **GSI:** `UserIdIndex` on `user_id` (full projection) — lists all destinations for a user
- **Encryption:** SSE
- **PITR:** Enabled
- **TTL:** Not used
- **Purpose:** User-defined export destinations. Stores type (e.g., `google_docs`), Google Docs target folder ID, job selector config (all jobs, specific jobs, or job tags), and email notification setting.

#### DocsExports Table

- **Resource name:** `DocsExports`, `snowscrape-{stage}-DocsExports`
- **Partition key:** `export_id` (string, UUID)
- **GSIs:**
  - `JobIdIndex` on `job_id` (full projection) — track exports for a given job
  - `UserIdIndex` on `user_id` (full projection) — list all user exports
- **Encryption:** SSE
- **PITR:** Enabled
- **TTL:** Enabled on `ttl` attribute — 90-day retention (created_at + 90 days)
- **Purpose:** Async export delivery log. Stores destination ID, export status (queued/processing/success/failed), Google Doc ID, template name (structured_log/compact_list/narrative), error message if failed, and delivery timestamp. Indexed for audit trails and retry/replay.

#### Billing Flow Diagram

```
Clerk signup
   ↓
Next.js middleware (60-second cookie cache of subscription status)
   ↓ (no subscription found)
/onboarding/checkout — single CTA → POST /billing/checkout
   ↓
Stripe Checkout (14-day trial of Pro, card required at signup)
   ↓
checkout.session.completed webhook fires to API Gateway
   ↓
backend/billing_handler.stripe_webhook_handler
  ├─ idempotency check via BillingWebhookDedup (conditional put on event_id)
  └─ _handle_checkout_completed
       └─ Subscriptions row created with status=trialing, trial_end set
   ↓
Frontend redirected to /dashboard?checkout=success
```

### SQS Queues (6)

| Queue | Visibility | Retention | Max Retries | DLQ |
|-------|-----------|-----------|-------------|-----|
| SnowscrapeJobQueue | 15 min | 4 days | 3 | SnowscrapeJobDLQ |
| SnowscrapeJobDLQ | 5 min | 14 days | - | - |
| SnowscrapeWebhookQueue | 60s | 4 days | 3 | SnowscrapeWebhookDLQ |
| SnowscrapeWebhookDLQ | 60s | 14 days | - | - |
| DocsExportQueue | 30s | 4 days | 3 | DocsExportDLQ |
| DocsExportDLQ | 60s | 14 days | - | - |

### S3 Bucket

**Name:** `snowscrape-results-{ACCOUNT_ID}-{REGION}`
**Versioning:** Enabled
**Lifecycle:**
- 90 days: Transition to GLACIER
- 365 days: Delete
- 7 days: Abort incomplete multipart uploads

**Encryption:** AES256 (SSE-S3)

### API Gateway

- **HTTP API (V2)** with 23 endpoints (migrated from REST API V1)
- CORS restricted to stage-specific frontend origin
- Lower latency and cost vs V1
- Request validation handled by Python validators (not gateway-level)

---

## Environment Variables

### Backend (Lambda)

| Variable | Source | Description |
|----------|--------|-------------|
| CLERK_JWT_PUBLIC_KEY | SSM | Clerk JWT verification key |
| CLERK_JWT_SECRET_KEY | SSM | Clerk secret key |
| DYNAMODB_JOBS_TABLE | sst.config.ts | Jobs table name |
| DYNAMODB_URLS_TABLE | sst.config.ts | URLs table name |
| DYNAMODB_SESSION_TABLE | sst.config.ts | Sessions table name |
| DYNAMODB_TEMPLATES_TABLE | sst.config.ts | Templates table name |
| DYNAMODB_WEBHOOKS_TABLE | sst.config.ts | Webhooks table name |
| DYNAMODB_WEBHOOK_DELIVERIES_TABLE | sst.config.ts | Delivery logs table |
| DYNAMODB_PROXY_POOL_TABLE | sst.config.ts | Proxy pool table |
| DYNAMODB_CONNECTIONS_TABLE | sst.config.ts | WebSocket connections |
| DYNAMODB_SUBSCRIPTIONS_TABLE | sst.config.ts | Billing subscriptions table |
| DYNAMODB_API_KEYS_TABLE | sst.config.ts | API keys table |
| DYNAMODB_BILLING_WEBHOOK_DEDUP_TABLE | sst.config.ts | Stripe webhook idempotency table |
| S3_BUCKET | sst.config.ts | Results storage bucket |
| SQS_JOB_QUEUE_URL | sst.config.ts | Job processing queue URL |
| SQS_WEBHOOK_QUEUE_URL | sst.config.ts | Webhook delivery queue URL |
| CORS_ALLOWED_ORIGIN | sst.config.ts | Stage-specific CORS origin |
| SNOWGLOBE_URL | sst.config.ts | Observatory API endpoint |
| SNOWGLOBE_API_KEY | env var | Observatory API key |
| RESIDENTIAL_PROXY_URL | env var | Proxy service URL (optional) |

**Stripe (from Doppler `sf-snowscrape`)**

| Variable | dev value (test mode) | prd value (live mode) |
|--------------------------------|--------------------------|--------------------------|
| STRIPE_SECRET_KEY | sk_test_... | sk_live_... |
| STRIPE_WEBHOOK_SECRET | whsec_UjI4rADiURdTnW4S09LRlZSDNVq2Rww4 | whsec_Iql4Wm2gDInz48oMbMumwalReaiYbvcq |
| STRIPE_PRICE_PRO_MONTHLY | price_1TUYHnAnsCk0eFqBMfkFoAaj | price_1TUf3bAhxqX4McFQyyCQu6Tq |
| STRIPE_PRICE_BUSINESS_MONTHLY | price_1TUYHzAnsCk0eFqBcXokmvKv | price_1TUf3mAhxqX4McFQlhAp2mCF |
| STRIPE_PORTAL_CONFIG_ID | bpc_1TUYIIAnsCk0eFqBGb41J2Zv | bpc_1TUf3vAhxqX4McFQ2R2Tb72j |

**Stripe Webhook Endpoints**

| Stage | Webhook ID | URL | Subscribed events |
|-------|------------|-----|-------------------|
| dev (test) | we_1TUat5AnsCk0eFqBGBqPX87U | `https://g5vmashyda.execute-api.us-east-2.amazonaws.com/billing/webhook` | 5 (see below) |
| prd (live) | we_1TUfJPAhxqX4McFQM0W5R5M7 | `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com/billing/webhook` | 5 (see below) |

**Stripe Customer Portal Configuration**

Configure once per stage in Stripe dashboard → Settings → Billing → Customer portal. Match these exact settings on both test mode and live mode:

- Customers can cancel subscriptions — at end of billing period
- Customers can switch plans — both Pro and Business prices selected
- Customers can update payment methods
- Show invoice history
- Allow invoice download
- Promotion codes: disabled (out of scope for MVP)
- Default return URL: `http://localhost:3001/dashboard/settings` (dev), `https://<prod-domain>/dashboard/settings` (prd)

Webhook endpoint registered per stage — the SST-generated API Gateway URL:
`https://<api-id>.execute-api.us-east-2.amazonaws.com/billing/webhook`

Subscribed Stripe events:
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

**Google Docs OAuth (from Doppler `sf-snowscrape`)**

| Variable | Description |
|----------|-------------|
| GOOGLE_OAUTH_CLIENT_ID | Google Cloud OAuth 2.0 client ID |
| GOOGLE_OAUTH_CLIENT_SECRET | Google Cloud OAuth 2.0 client secret |
| GOOGLE_OAUTH_REDIRECT_URI | Backend callback URL (e.g., `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com/integrations/google/callback`) |

### Frontend (Vercel)

| Variable | Public | Description |
|----------|--------|-------------|
| NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY | Yes | Clerk frontend key |
| CLERK_SECRET_KEY | No | Clerk server-side key |
| NEXT_PUBLIC_API_URL | Yes | Backend API Gateway URL |
| NEXT_PUBLIC_WS_URL | Yes | WebSocket API URL |
| NEXT_PUBLIC_SENTRY_DSN | Yes | Sentry error tracking |

---

## Google Docs Export

- **OAuth scopes**: `drive.file` (create-only), `drive.metadata.readonly` (folder picker support), `documents` (write to Docs), `openid`/`email`/`profile`.
- **Token storage**: Refresh tokens KMS-encrypted (alias/snowscrape-{stage}-oauth-tokens) before persistence to GoogleAccounts. Access tokens are not stored — refreshed per-export.
- **Delivery**: Post-job-completion fan-out via DocsExportQueue (SQS, 3 retries + DLQ). Triggered alongside webhook delivery in job_manager._on_job_completed.
- **Routes**: `/integrations/google/{auth-url, callback, GET, DELETE}`, `/export-destinations/{POST, GET, DELETE/{id}}`.
- **Billing**: Not metered against plan limits in v1.0.
- **KMS Key**: `alias/snowscrape-{stage}-oauth-tokens` — automatically created by SST and exposed via OAUTH_TOKEN_KMS_KEY_ID env var.
- **Env vars**: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI (from Doppler); OAUTH_TOKEN_KMS_KEY_ID (from SST output).

---

## Monitoring & Observability

- **X-Ray Tracing:** Enabled for Lambda (API Gateway disabled due to role issue)
- **CloudWatch Logs:** 14-day retention, all Lambda functions
- **CloudWatch Alarms:** High error rate, DLQ messages, Lambda errors/throttles, 5xx errors
- **Sentry:** Frontend error tracking with session replay
- **SnowGlobe Observatory:** Custom metrics (job lifecycle, crawl performance)

---

## Security

- **Auth:** Clerk JWT tokens validated on every request
- **CORS:** Stage-specific origins (no wildcards)
- **Encryption at rest:** DynamoDB SSE, S3 AES256, SQS KMS
- **Encryption in transit:** HTTPS enforced (HSTS headers)
- **Secrets:** Stored in AWS SSM Parameter Store (SecureString)
- **SSRF Protection:** Private IP ranges blocked before scraping
- **Input Validation:** XPath function whitelist, regex timeout, URL scheme validation

---

## Known Limitations

1. **JavaScript rendering:** GLIBC incompatibility blocks Playwright on Lambda (Tier 3/4 scraping non-functional)
2. **No Redis cache:** Planned but not yet implemented
3. **Single region:** No multi-region failover
4. **No VPC:** Lambda runs in default VPC

---

## Cost Estimate

| Resource | Dev/Month | Prod/Month (10K jobs) |
|----------|-----------|----------------------|
| Lambda | $5-10 | $50-100 |
| DynamoDB | $2-5 | $20-50 |
| SQS | $1-2 | $5-10 |
| S3 | $1-2 | $10-30 |
| API Gateway | $3-5 | $30-50 |
| CloudWatch | $5-10 | $20-40 |
| **Total** | **$17-34** | **$135-280** |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-02 | Added Google Docs export destination feature. New AWS resources: KMS key (alias/snowscrape-{stage}-oauth-tokens), 3 DynamoDB tables (GoogleAccounts, ExportDestinations, DocsExports), SQS queue+DLQ (DocsExportQueue, DocsExportDLQ), and SQS-subscriber Lambda. New env vars: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI (from Doppler), OAUTH_TOKEN_KMS_KEY_ID (from SST). New routes: /integrations/google/* and /export-destinations/*. | Alex Diaz |
| 2026-05-07 | Billing MVP shipped: added Subscriptions, ApiKeys, BillingWebhookDedup tables; trial-only entry flow with Stripe Customer Portal for plan management; idempotent webhook handler. Stripe products provisioned per stage in Doppler sf-snowscrape. | Alex Diaz |
| 2026-05-08 | Billing MVP went live in prd: live-mode Stripe products + portal config + webhook registered; SST deployed to prod stage; Vercel frontend deployed with `typescript.ignoreBuildErrors=true` (temporary, pending @snowforge/ui v3→v4 migration). Bugs fixed during smoke: middleware/proxy collision, Stripe API 2024-09+ schema (current_period_end moved to items[]), DynamoDB Decimal JSON serialization, stale subscription-status cookie, @clerk/types duplicate version, Clerk v7 sign-in/up prop renames, snowforge-ui v4 useSidebar API. | Alex Diaz |
| 2026-03-25 | Added Firecrawl integration for Tier 3/4 scraping (JS rendering + anti-bot) | Claude |
| 2026-03-25 | Added AI-powered data extraction via Claude (ai_extractor.py) | Claude |
| 2026-03-25 | Added WebSocket end-to-end pipeline for real-time job updates | Claude |
| 2026-03-25 | Documentation audit: updated all stale READMEs and created PROGRESS.md | Claude |
| 2026-02-06 | Migrated from Serverless Framework to SST Ion (TypeScript IaC) | Claude |
| 2026-02-06 | Merged frontend + backend into unified monorepo | Claude |
| 2026-02-06 | Migrated API Gateway from V1 (REST) to V2 (HTTP) | Claude |
| 2026-02-06 | Added Connections table (8th DynamoDB table) | Claude |
| 2026-02-06 | Migrated Python deps from pip/requirements.txt to uv/pyproject.toml | Claude |
| 2026-02-06 | Initial infrastructure documentation created | Claude |
| 2026-02-06 | Moved Clerk keys from hardcoded to SSM Parameter Store | Claude |
| 2026-02-06 | Restricted CORS to stage-specific origins | Claude |
| 2026-02-06 | Enabled encryption at rest on all data stores | Claude |
| 2026-02-06 | Added SSRF protection, XPath whitelist, regex timeout | Claude |
