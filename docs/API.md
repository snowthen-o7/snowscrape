# SnowScrape API: Programmatic Access Quickstart

SnowScrape exposes a REST API so you can create and manage scraping jobs without the
dashboard. This guide covers authenticating with an API key and the common job
lifecycle. The full machine-readable contract is in
[`backend/openapi.yml`](../backend/openapi.yml).

## 1. Create an API key

In the dashboard, go to **Settings -> API Keys** and create a key. The full value
(`sk_live_...`) is shown **once** at creation and stored only as a hash afterward, so
copy it immediately. You can hold up to 10 active keys and revoke any of them from the
same screen.

API keys authenticate the entire `/jobs` data-plane: creating, listing, reading,
updating, and deleting jobs; the pause / resume / cancel / refresh actions; reading
crawls; and downloading or previewing results. Control-plane operations (managing API
keys, billing, templates, webhooks, and OAuth integrations) stay dashboard-only and
require a Clerk session, so a leaked key cannot mint new keys or change billing.

## 2. Authenticate

Pass the key as a bearer token on every request:

```
Authorization: Bearer sk_live_YOUR_API_KEY_HERE
```

The production base URL is the API Gateway stage URL for your environment, for example:

```
https://2pg2gj4048.execute-api.us-east-2.amazonaws.com/prod
```

A revoked or invalid key returns `401 Unauthorized`. Requesting a job you do not own
returns `403 Forbidden`.

## 3. Create a job

`direct_url` jobs scrape a single URL template; `csv` jobs read a list of URLs from a
CSV source. Minimal `direct_url` example:

```bash
curl -X POST "$BASE_URL/jobs" \
  -H "Authorization: Bearer $SNOWSCRAPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily product price",
    "source_type": "direct_url",
    "url_template": "https://example.com/products/{{date:Y-m-d}}",
    "rate_limit": 2,
    "queries": [
      { "name": "title", "type": "xpath", "query": "//h1/text()", "join": false },
      { "name": "price", "type": "xpath", "query": "//span[@class=\"price\"]/text()", "join": false }
    ]
  }'
```

Response:

```json
{ "message": "Job created successfully", "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }
```

## 4. List jobs and check status

```bash
curl "$BASE_URL/jobs/status?limit=50" \
  -H "Authorization: Bearer $SNOWSCRAPE_API_KEY"
```

Paginate by passing the returned `last_key` back as the `last_key` query parameter.
Fetch one job with `GET /jobs/{job_id}`.

## 5. Trigger a run and download results

Force an immediate crawl (outside the schedule), then download once it completes:

```bash
# Re-crawl now
curl -X POST "$BASE_URL/jobs/$JOB_ID/refresh" \
  -H "Authorization: Bearer $SNOWSCRAPE_API_KEY"

# Get a pre-signed download URL (json, csv, xlsx, parquet, or sql)
curl "$BASE_URL/jobs/$JOB_ID/download?format=csv" \
  -H "Authorization: Bearer $SNOWSCRAPE_API_KEY"
```

`download` returns a short-lived pre-signed S3 URL in `download_url`. For an in-app style
paginated view of the rows, use `GET /jobs/{job_id}/preview?page=1&page_size=50`.

## 6. Job actions

| Action  | Request                                  |
|---------|------------------------------------------|
| Pause   | `PATCH /jobs/{job_id}/pause`             |
| Resume  | `PATCH /jobs/{job_id}/resume`            |
| Cancel  | `PATCH /jobs/{job_id}/cancel`            |
| Refresh | `POST  /jobs/{job_id}/refresh`           |
| Update  | `PUT   /jobs/{job_id}` (same body as create) |
| Delete  | `DELETE /jobs/{job_id}`                  |

## Rate limits

API Gateway enforces a burst limit of 200 concurrent requests and a sustained 100
requests/second across the account. Per-plan page quotas apply to the scraping work
itself and are enforced at job-create time; a `402` means the subscription is inactive
or the quota is exhausted.

## Notes

- All authenticated requests use the same `Authorization: Bearer ...` header whether the
  token is a Clerk session JWT (dashboard) or an `sk_live_...` API key (programmatic).
- Webhooks (job lifecycle events) are configured in the dashboard. They are part of the
  control-plane, so they cannot be managed with an API key today.
- The `/jobs` data-plane is the supported programmatic surface. Templates and export
  destinations are dashboard-managed for now.
