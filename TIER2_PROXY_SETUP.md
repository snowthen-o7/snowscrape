# Tier 2 Proxy Setup Guide

Tier 2 scraping uses residential proxies to bypass IP-based blocking. This guide explains how to configure proxy services for SnowScrape.

## Proxy Options

SnowScrape Tier 2 supports three proxy options (in order of priority):

1. **Runtime proxy config** (passed directly to `scrape_tier_2()`)
2. **Residential proxy service** (via `RESIDENTIAL_PROXY_URL` environment variable)
3. **AWS EC2 proxy pool** (existing infrastructure via `proxy_manager.py`)

## Option 1: Residential Proxy Services (Recommended for Testing)

Residential proxies rotate real residential IP addresses to avoid detection.

### Recommended Providers

| Provider | Cost | Trial | Notes |
|----------|------|-------|-------|
| **Bright Data** | ~$500/month (40GB) | 7-day free trial | Most reliable, largest pool |
| **Oxylabs** | ~$300/month | Free trial | Good performance |
| **SmartProxy** | ~$75/month (5GB) | 3-day money back | Budget-friendly |
| **NetNut** | ~$300/month | Free trial | Fast, datacenter-quality |

### Setup Instructions

#### 1. Sign Up for Bright Data (Example)

1. Go to https://brightdata.com
2. Sign up for a free trial (no credit card required)
3. Create a "Residential Proxies" zone
4. Get your proxy credentials:
   - Username: `your-customer-id-zone-residential`
   - Password: `your-password`
   - Proxy host: `brd.superproxy.io:22225`

#### 2. Set Environment Variable

**Local Development:**
```bash
export RESIDENTIAL_PROXY_URL="http://your-customer-id-zone-residential:your-password@brd.superproxy.io:22225"
```

**Windows (PowerShell):**
```powershell
$env:RESIDENTIAL_PROXY_URL="http://your-customer-id-zone-residential:your-password@brd.superproxy.io:22225"
```

**AWS Lambda:**
```bash
# Deploy with environment variable
RESIDENTIAL_PROXY_URL="http://user:pass@proxy:port" npx serverless deploy --stage dev
```

Or add to `.env` file (for local development):
```
RESIDENTIAL_PROXY_URL=http://your-customer-id-zone-residential:your-password@brd.superproxy.io:22225
```

#### 3. Verify Setup

Test that Tier 2 works:

```python
from tiered_scraper import scrape_tier_2

# Should now work with proxy
result = scrape_tier_2("https://www.costco.com/")
print(f"Tier used: {result['tier_used']}")
print(f"Status: {result['status_code']}")
```

## Option 2: AWS EC2 Proxy Pool (Production)

Uses existing `proxy_manager.py` infrastructure with self-hosted Squid proxies on EC2.

### Setup Required:

1. Deploy EC2 instances with Squid proxy in multiple regions
2. Store proxy URLs in AWS Secrets Manager (`snowscrape/proxy-pool`)
3. Configure DynamoDB table (`SnowscrapeProxyPool`)
4. No environment variable needed - automatically detected

### Secret Format:

```json
{
  "proxies": [
    {
      "url": "http://user:pass@1.2.3.4:3128",
      "region": "us-east-1",
      "status": "healthy"
    },
    {
      "url": "http://user:pass@5.6.7.8:3128",
      "region": "eu-west-1",
      "status": "healthy"
    }
  ]
}
```

## Cost Comparison

### Residential Proxies (Per Month)

| Volume | Bright Data | SmartProxy | Oxylabs |
|--------|-------------|------------|---------|
| 5 GB   | $300        | $75        | $180    |
| 40 GB  | $500        | $400       | $600    |
| 100 GB | $1000       | $850       | $1200   |

**SnowScrape Usage:**
- Average page size: ~500KB
- 1000 pages ≈ 500MB
- 10,000 pages ≈ 5GB (~$75-300/month)
- 100,000 pages ≈ 50GB (~$500-1200/month)

### AWS EC2 Proxies (Self-Hosted)

- **t3.micro** (1 proxy): ~$7/month + bandwidth
- **Bandwidth**: $0.09/GB (outbound)
- **Total for 50GB**: ~$50/month (10 instances)

**Pros:** Lower cost at scale, full control
**Cons:** Setup complexity, maintenance required

## Testing Tier 2

### Test with Forever21 (Should Still Use Tier 1)
```bash
# Forever21 doesn't block, should stay on Tier 1
curl -X POST http://localhost:3001/api/scraper/preview \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.forever21.com/us/2000497067.html"}'
```

### Test with Costco (Should Escalate to Tier 2)
```bash
# Costco blocks Tier 1, should escalate to Tier 2 with proxy
curl -X POST http://localhost:3001/api/scraper/preview \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.costco.com/"}'
```

**Expected behavior:**
- Tier 1 fails with 403 Forbidden
- System automatically escalates to Tier 2
- Uses residential proxy
- Returns page content successfully
- Shows "Advanced Scraping Used" banner with Tier 2 cost ($0.005/page)

## Troubleshooting

### Error: "Tier 2 requires proxy configuration"

**Solution:** Set `RESIDENTIAL_PROXY_URL` environment variable or configure AWS proxy pool.

### Error: "407 Proxy Authentication Required"

**Solution:** Check your proxy credentials (username/password).

### Error: "Proxy connection timeout"

**Solution:**
1. Verify proxy is reachable: `curl -x http://user:pass@proxy:port https://httpbin.org/ip`
2. Check firewall rules
3. Increase timeout parameter

### Tier 2 Still Getting Blocked

**Solution:** Site may need Tier 3 (browser mode) - coming in Week 2.

## Next Steps

Once Tier 2 is working:
- **Week 2:** Implement Tier 3 (Playwright browser mode)
- **Week 3:** Implement Tier 4 (CAPTCHA solving)
- **Week 4:** Production deployment with domain intelligence

## Resources

- [Bright Data Documentation](https://docs.brightdata.com/)
- [Oxylabs Proxy Guide](https://oxylabs.io/products/residential-proxies)
- [SmartProxy Setup](https://help.smartproxy.com/)
