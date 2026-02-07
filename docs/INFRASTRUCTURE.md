# SnowScrape Infrastructure

**Last Updated:** 2026-02-06 (SST Ion Migration)
**AWS Account ID:** 282128795857
**Primary Region:** us-east-2

---

## Architecture Overview

SnowScrape is a serverless web scraping platform deployed on AWS.

```
[Vercel] ──HTTPS──> [API Gateway] ──> [Lambda Functions]
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
              [DynamoDB]              [SQS Queues]            [S3 Bucket]
              (8 tables)           (2 queues + 2 DLQs)       (results)
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

### DynamoDB Tables (8)

| Table | Partition Key | Sort Key | GSIs | Encryption | PITR |
|-------|--------------|----------|------|------------|------|
| Jobs | job_id (S) | - | StatusIndex (status), ScheduleIndex (jobStatus + nextRun) | SSE | Enabled |
| Urls | job_id (S) | url (S) | StatusIndex (status) | SSE | Enabled |
| Sessions | job_id (S) | - | - | SSE | Enabled |
| Templates | template_id (S) | - | UserIdIndex (user_id) | SSE | Enabled |
| Webhooks | webhook_id (S) | - | UserIdIndex (user_id) | SSE | Enabled |
| WebhookDeliveries | delivery_id (S) | - | WebhookIdIndex (webhook_id + timestamp) | SSE | Enabled |
| ProxyPool | proxy_id (S) | - | - | SSE | Enabled |
| Connections | connection_id (S) | - | - (TTL enabled) | SSE | - |

All tables use PAY_PER_REQUEST billing mode.

### SQS Queues (4)

| Queue | Visibility | Retention | Max Retries | DLQ |
|-------|-----------|-----------|-------------|-----|
| SnowscrapeJobQueue | 15 min | 4 days | 3 | SnowscrapeJobDLQ |
| SnowscrapeJobDLQ | 5 min | 14 days | - | - |
| SnowscrapeWebhookQueue | 60s | 4 days | 3 | SnowscrapeWebhookDLQ |
| SnowscrapeWebhookDLQ | 60s | 14 days | - | - |

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
| S3_BUCKET | sst.config.ts | Results storage bucket |
| SQS_JOB_QUEUE_URL | sst.config.ts | Job processing queue URL |
| SQS_WEBHOOK_QUEUE_URL | sst.config.ts | Webhook delivery queue URL |
| CORS_ALLOWED_ORIGIN | sst.config.ts | Stage-specific CORS origin |
| SNOWGLOBE_URL | sst.config.ts | Observatory API endpoint |
| SNOWGLOBE_API_KEY | env var | Observatory API key |
| RESIDENTIAL_PROXY_URL | env var | Proxy service URL (optional) |

### Frontend (Vercel)

| Variable | Public | Description |
|----------|--------|-------------|
| NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY | Yes | Clerk frontend key |
| CLERK_SECRET_KEY | No | Clerk server-side key |
| NEXT_PUBLIC_API_URL | Yes | Backend API Gateway URL |
| NEXT_PUBLIC_WS_URL | Yes | WebSocket API URL |
| NEXT_PUBLIC_SENTRY_DSN | Yes | Sentry error tracking |

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
