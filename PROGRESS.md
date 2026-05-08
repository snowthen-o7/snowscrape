# SnowScrape -- Progress & Launch Readiness

**Last Updated:** 2026-05-08
**Launch Readiness:** ~95% (live, awaiting first $0 trial-signup smoke)
**Build Status:** PASSES
**Test Coverage:** ~60-70% (unit + integration; Playwright setup present)

---

## What's DONE

### Infrastructure (SST Ion Migration -- Complete)
- Migrated from Serverless Framework to SST Ion v3 (TypeScript IaC, Pulumi engine)
- Merged frontend + backend into unified monorepo with pnpm workspaces
- Migrated API Gateway from V1 (REST) to V2 (HTTP) -- lower latency and cost
- Migrated Python deps from pip/requirements.txt to uv/pyproject.toml
- 29 Lambda functions deployed and operational
- 8 DynamoDB tables with PAY_PER_REQUEST billing, SSE encryption, PITR
- 4 SQS queues (job + webhook, each with DLQ)
- S3 results bucket with versioning and Glacier lifecycle
- Secrets moved from hardcoded to SSM Parameter Store
- CORS restricted to stage-specific origins
- SSRF protection, XPath whitelist, regex timeout validation
- CI/CD via GitHub Actions (frontend + backend workflows)

### 4-Tier Scraping System (Complete)
- Tier 1: Direct HTTP requests (static HTML)
- Tier 2: Residential proxy rotation (IP-blocked sites)
- Tier 3: Firecrawl JS rendering (JavaScript SPAs)
- Tier 4: Firecrawl anti-bot bypass (bot-protected sites)
- Automatic escalation on failure

### AI-Powered Extraction (Complete)
- Claude integration via `ai_extractor.py`
- Natural language queries against scraped content
- Structured data extraction from unstructured HTML

### Real-Time WebSocket (Complete)
- API Gateway V2 WebSocket API
- Live job progress updates
- Connection management with DynamoDB (TTL-enabled)

### Webhook System (Complete)
- Event-driven notifications (job.created, started, completed, failed, cancelled)
- SQS-based async delivery with retry logic (max 3 attempts)
- HMAC SHA256 signatures for security
- Delivery tracking and DLQ for failed deliveries
- Webhook management UI

### Template System (Complete)
- Save and reuse scraping configurations
- Template CRUD with user-scoped access

### Visual Job Builder (Complete)
- No-code job creation UI
- Query builder for XPath, Regex, JSONPath, CSS selectors

### Multi-Format Export (Complete)
- JSON, CSV, XLSX, Parquet, SQL export
- Server-side conversion with S3 caching

### Frontend (Complete)
- Next.js 16 with App Router
- Tailwind CSS 4.x with semantic color tokens (dark mode)
- Radix UI component library
- Collapsible sidebar layout (reference implementation for SnowForge LLC)
- Marketing landing pages
- Sentry error monitoring
- 42 unit tests (Vitest), Playwright E2E setup

### Billing / Stripe Integration (Live in production)

- 14-day Pro trial with card-required checkout (no free starter tier)
- Stripe Customer Portal handles all plan changes, cancellations, payment updates (no in-app plan picker)
- 3 paid tiers: Pro $49/mo, Business $149/mo, Enterprise (sales-led)
- Backend: idempotent Stripe webhook handler with `BillingWebhookDedup` table, race-fixed period-end updates, hard 402 gate at job-create when subscription inactive, fail-open usage counters
- Frontend: subscription-status proxy gate (60s cookie cache, only caches `trialing`/`active`), `/onboarding/checkout` and `/billing/locked` screens, Settings → Billing tab live data, one-time-secret API-key modal
- Pricing page: dropped Starter card, 14-day-trial hero, `<PricingCTA>` routes signed-out → /sign-up, signed-in active → portal, signed-in no-sub → /onboarding/checkout
- Tests: 11 backend webhook + integration tests, 3 Vitest unit tests, 1 Playwright E2E (gated on Clerk test user)
- **Deployed to dev** (test mode) on 2026-05-07: smoke test passed end-to-end (signup → checkout → trial → cancel → past-due lockout → webhook idempotency replay)
- **Deployed to prd** (live mode) on 2026-05-08: backend + frontend live; awaiting first real $0 trial signup as final acceptance
- Live Stripe identifiers (test mode): Pro `price_1TUYHnAnsCk0eFqBMfkFoAaj`, Business `price_1TUYHzAnsCk0eFqBcXokmvKv`, Portal config `bpc_1TUYIIAnsCk0eFqBGb41J2Zv`, Webhook `we_1TUat5AnsCk0eFqBGBqPX87U`
- Live Stripe identifiers (live mode): Pro `price_1TUf3bAhxqX4McFQyyCQu6Tq`, Business `price_1TUf3mAhxqX4McFQlhAp2mCF`, Portal config `bpc_1TUf3vAhxqX4McFQ2R2Tb72j`, Webhook `we_1TUfJPAhxqX4McFQM0W5R5M7`
- Production frontend: `https://scrape.snowforge.dev` (Vercel)
- Production API: `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com`

---

## What's NOT DONE

### Analytics Dashboard (UI only, no data)
- Dashboard pages exist but display mock/placeholder data
- No real analytics pipeline connected

### API Key Authentication (Backend complete, public-endpoint auth not wired)
- Backend `api_key_handler.py` and Settings → API Keys tab fully implemented (one-time-secret modal, list/create/revoke)
- API keys can be created and managed
- BUT: external API calls to `/jobs` etc. still require Clerk JWT -- there's no `Authorization: Bearer sk_live_...` middleware yet
- Sub-project #2 of launch sequence

### Notification System (Partial)
- Webhook notifications work
- Email notifications not implemented
- In-app notification center not built

### Known Technical Limitations
- JavaScript rendering: GLIBC incompatibility blocks Playwright on Lambda (Tiers 3/4 use Firecrawl instead)
- No Redis cache (planned but not implemented)
- Single region (us-east-2, no multi-region failover)
- Lambda runs in default VPC

---

## Estimates to Revenue

| Work Item | Estimate | Priority |
|-----------|----------|----------|
| First real $0 trial signup as final live smoke | hours | CRITICAL -- final acceptance |
| API key auth on public endpoints | 1 week | MEDIUM |
| Real analytics data pipeline | 2-3 weeks | HIGH |
| Email notifications | 1 week | MEDIUM |
| In-app notification center | 1 week | LOW |
| `@snowforge/ui` v3→v4 migration + revert `typescript.ignoreBuildErrors` | 1-2 hours | LOW (debt) |

---

## Architecture Reference

See [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md) for full details on:
- 29 Lambda functions with memory/timeout configs
- 8 DynamoDB tables with GSIs and encryption
- 4 SQS queues with retry and DLQ configuration
- S3 lifecycle policies
- Environment variables
- Cost estimates
- Security policies
