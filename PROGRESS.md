# SnowScrape -- Progress & Launch Readiness

**Last Updated:** 2026-06-06
**Launch Readiness:** ~98% (live; Google Docs destination backend complete, awaiting Alex's Google Cloud OAuth client + deploy)
**Build Status:** PASSES (backend unit suite 304/304 green as of 2026-06-06; was 11 red before today's fix)
**Test Coverage:** ~60-70% (unit + integration; Playwright setup present)

### Recent -- 2026-06-06
- API-key auth wired across the entire /jobs data-plane (claude-main, pending Alex's merge to main). Programmatic API access (the launch "sub-project #2") was blocked because `validate_api_key` existed but was never called: every public endpoint still required a Clerk JWT, so the Settings -> API Keys feature produced keys that did not actually authenticate anything. Added a single auth resolver `resolve_user_id(token)` in `utils.py` that accepts either a SnowScrape API key (`sk_live_...`, checked first by prefix) or a Clerk session JWT, returning the owning user_id (raising on an invalid credential so callers keep their existing 401 path). Wired it into all 13 /jobs data-plane handlers (create, list/status, get, update, delete, pause, cancel, resume, refresh, crawls list+get, download, preview). Control-plane endpoints (api-keys CRUD, billing, integrations/OAuth, templates, webhooks, destinations) intentionally stay Clerk-only. Billing gates are unaffected: they key off user_id, which the resolver supplies for API-key callers too. TDD: 4 resolver unit tests + 2 end-to-end API-key integration tests (valid key authenticates a /jobs read; revoked key -> 401). Evidence: full backend suite 333 passed (308 unit + 25 integration), up from 327.
- Backend red-signal fix (claude-main, pending Alex's merge to main). The backend unit suite was red: 11 failing tests (4 in `test_utils.py`, 7 in `test_ai_extractor.py`). Root causes and fixes:
  - **Real production bug in CSV URL parsing.** `parse_links_from_file`'s pandas path is dead in production (pandas is intentionally not bundled in the Lambda, so it is not in `backend/pyproject.toml` and never imports), meaning the manual `csv.reader` fallback is the ONLY path that runs in prod. That fallback did not skip the header row, did not skip empty cells, and did not support the `'default'` auto-detect column option, so every CSV-sourced job ingested the header text as a bogus URL and could not auto-detect a URL column. Rewrote the fallback to mirror the pandas semantics (row 0 = header, resolve the column against the header, skip the header row and empty cells, support `'default'` via `detect_url_column`). 3 previously-failing `TestParseLinksFromFile` tests now encode the correct behavior and pass.
  - **Stale auth test.** `test_extract_token_case_sensitive` asserted a lowercase `authorization` header yields no token, but `extract_token_from_event` deliberately accepts it (API Gateway V2 lowercases all header names). Corrected the test to match the intended, correct behavior.
  - **AI-extractor test mock drift.** `test_ai_extractor.py` patches `ai_extractor.anthropic`, but the module lazy-imported `anthropic` inside `_get_client`, so the attribute did not exist at patch time (7 failures). Moved `import anthropic` to module scope (it is already a hard dependency); client construction stays lazy. No behavior change.
  - Evidence: backend unit suite 304 passed / 0 failed (was 293 passed, 11 failed); integration suite 23 passed.

### Recent -- 2026-06-05
- Frontend: wired the export-destination selector into the AI-assisted and Visual builder job-creation flows. Previously only the manual form rendered `DestinationSelector`; jobs created via AI/Visual silently dropped any chosen destinations and could never auto-export. Added `export_destination_ids` (plus `source_type`, `url_template`) to `CreateJobDTO`, extracted the `buildAiJobPayload` pure helper with 6 unit tests, and rendered `DestinationSelector` in both flows. Frontend suite 51/51 green. Merged to `claude-main` via PR #6; awaiting Alex's `claude-main -> main` review.

### Recent -- 2026-06-03
- Backend fix: `job_manager.py` now propagates `results_s3_key` into `job_data` before the docs-export fan-out (without it, the export Lambda had no S3 results to read). Committed + pushed to `main`, alongside the Google Docs destination implementation plan and a user-action checklist (`docs/superpowers/plans/2026-06-01-google-docs-destination.md`, `2026-06-02-google-docs-destination-user-checklist.md`).
- Walked Alex through the Google Cloud Console OAuth setup (create project, enable Drive + Docs APIs, configure consent screen, create OAuth client). This is step 1 of the user checklist and the active remaining blocker before the Google Docs destination is live in prod. Context: scoped while evaluating a LinkedIn-post-scraping freelance gig.

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

### Google Docs Export Destination (Backend complete; code-ready for deploy)
- OAuth flow for connecting user Google accounts (drive.file + documents scopes; drive.metadata.readonly deferred to v1.1 folder picker)
- KMS-encrypted refresh token storage (per-user)
- Export destinations CRUD (Google Docs as v1 target)
- SQS-triggered docs export Lambda: reads scrape results from S3, formats via three templates (structured_log, compact_list, narrative), writes to user's Drive folder via Google Docs batchUpdate API
- Fan-out from job completion handler: jobs can attach 0-10 destinations; results auto-export after each successful run
- Frontend UI: Integrations page (connect/disconnect Google), Destinations CRUD page, DestinationSelector inside the manual job creation form
- 50+ backend unit + integration tests covering OAuth, destinations, dispatcher, and export Lambda
- Deploy + Doppler secrets + Google Cloud Console OAuth client setup are user-action follow-ups
- Drive folder picker UI deferred to v1.1 (users paste folder ID for now)
- AI/Visual job creation forms now wired with destinations (2026-06-05, PR #6); manual form already had it

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

### API Key Authentication (jobs data-plane wired on claude-main; control-plane still Clerk-only)
- Backend `api_key_handler.py` and Settings → API Keys tab fully implemented (one-time-secret modal, list/create/revoke)
- API keys can be created and managed
- DONE (claude-main, 2026-06-06): `Authorization: Bearer sk_live_...` now authenticates the entire `/jobs` data-plane via `resolve_user_id` (create, list, get, update, delete, pause, cancel, resume, refresh, crawls, download, preview)
- Remaining: decide whether to extend API-key auth to the other data endpoints (templates, webhooks, export destinations); the control-plane (api-keys CRUD, billing, integrations/OAuth) stays Clerk-only by design. Public API docs / a quickstart for programmatic use would also help.
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
| API key auth on public endpoints | jobs data-plane DONE (2026-06-06); optional: extend to templates/webhooks/destinations + write API docs | MEDIUM |
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
