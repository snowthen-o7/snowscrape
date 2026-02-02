# Bot Protection Bypass Research

**Status:** Critical Priority
**Date:** 2026-02-01
**Problem:** Cannot scrape bot-protected sites like Costco, Amazon, Target, etc.
**Impact:** Significantly behind competition without this capability

---

## Current Situation

### What Fails

When attempting to scrape Costco with our current Python `requests` + BeautifulSoup approach:

```
403 Forbidden: This site appears to block automated access
```

**Why it fails:**
1. AWS Lambda IPs are known and blacklisted
2. HTTP client has identifiable fingerprint
3. No JavaScript execution (modern sites use JS challenges)
4. Predictable request patterns
5. Missing browser-like behavior

### What We're Up Against

Modern bot protection systems (Cloudflare, PerimeterX, Akamai, DataDome, etc.) use:

**1. IP Reputation**
- Blacklist known datacenter IPs (AWS, GCP, Azure)
- Track IP request rates and patterns
- Require residential IP addresses

**2. TLS Fingerprinting**
- Python `requests` has distinct TLS handshake
- Can identify automated tools vs real browsers
- Checks cipher suites, extensions, and order

**3. HTTP/2 Fingerprinting (JA3)**
- Unique fingerprints for HTTP clients
- Python requests library is easily identified
- Real browsers have specific fingerprints

**4. JavaScript Challenges**
- Browser fingerprinting (Canvas, WebGL, Audio)
- TLS/SSL fingerprinting at JS level
- Device motion/touch events
- Browser feature detection
- Proof-of-work challenges

**5. Behavioral Analysis**
- Mouse movement patterns
- Scroll behavior
- Click timing and patterns
- Time spent on page
- Navigation paths

**6. CAPTCHA**
- reCAPTCHA v2/v3
- hCaptcha
- Cloudflare Turnstile
- Custom challenges

---

## Solution Architecture

### Phase 1: Headless Browser Infrastructure (Required)

**Technology:** Playwright or Puppeteer with stealth plugins

**Why this is mandatory:**
- Executes JavaScript (required for modern sites)
- Real browser fingerprint
- Can solve JS challenges automatically
- Handles dynamic content

**Implementation:**

```python
# Use Playwright with stealth mode
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def scrape_with_browser(url):
    async with async_playwright() as p:
        # Use real browser, not headless (headless is detectable)
        browser = await p.chromium.launch(
            headless=False,  # Some sites detect headless mode
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = await context.new_page()

        # Apply stealth patches to avoid detection
        await stealth_async(page)

        # Add random delays (human-like behavior)
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(random.randint(2000, 5000))

        # Random mouse movements
        await page.mouse.move(random.randint(0, 1000), random.randint(0, 800))

        # Extract data
        content = await page.content()

        await browser.close()
        return content
```

**Deployment Options:**

1. **AWS Lambda + Lambda Layers**
   - Package Playwright/Chromium as Lambda layer
   - Increase timeout to 15 minutes
   - Increase memory to 3GB+
   - Cold start: 10-30 seconds

2. **AWS ECS/Fargate**
   - Better for long-running tasks
   - More memory/CPU available
   - Can run multiple browsers simultaneously
   - More expensive but more reliable

3. **Dedicated EC2 Instances**
   - Most control
   - Can use residential proxy pools
   - Best performance
   - Requires more DevOps

**Recommendation:** Start with Lambda + Layers, move to ECS if needed.

---

### Phase 2: Residential Proxy Network (Critical)

**Problem:** Even with real browsers, datacenter IPs are blocked.

**Solutions:**

#### Option A: Bright Data (Recommended)
- **Cost:** ~$500/month for 20GB
- **Pros:**
  - Largest residential proxy network
  - 72M+ IPs worldwide
  - Geo-targeting
  - Automatic rotation
  - High success rate on difficult sites
  - CAPTCHA solving included
- **Cons:**
  - Expensive
  - Pay per GB

**Integration:**
```python
proxy_config = {
    'server': 'http://brd-customer-{customer_id}-zone-{zone}:password@brd.superproxy.io:22225',
    'username': 'brd-customer-xxxxxxx-zone-residential',
    'password': 'your_password'
}

context = await browser.new_context(
    proxy=proxy_config,
    # ... other options
)
```

#### Option B: Oxylabs
- **Cost:** ~$300/month for 15GB
- **Similar to Bright Data but slightly cheaper
- Slightly smaller network

#### Option C: SmartProxy
- **Cost:** ~$225/month for 10GB
- Good for budget-conscious
- Smaller network, lower success rate on hard targets

#### Option D: Build Your Own (NOT Recommended)
- Requires managing residential IPs
- Legal/ethical concerns
- Unreliable
- More work than value

**Recommendation:** Start with Bright Data's trial, move to paid plan.

---

### Phase 3: Undetected Browser Techniques

**1. Undetected ChromeDriver (Python)**

```bash
pip install undetected-chromedriver
```

```python
import undetected_chromedriver as uc

driver = uc.Chrome(
    options=options,
    version_main=None,  # Auto-detect Chrome version
    use_subprocess=True
)
```

**2. Playwright Stealth Plugin**

```bash
pip install playwright-stealth
```

Patches over 30 detection points including:
- `navigator.webdriver`
- Chrome detection
- Permissions API
- Plugin inconsistencies
- Iframe contentWindow
- Hairline feature detection

**3. Browser Fingerprint Randomization**

```python
# Randomize viewport
viewport = {
    'width': random.choice([1366, 1920, 2560]),
    'height': random.choice([768, 1080, 1440])
}

# Randomize user agent (but keep it realistic)
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...',
    # ... rotation of real browser UAs
]

# Randomize timezone
timezones = ['America/New_York', 'America/Chicago', 'America/Los_Angeles']

context = await browser.new_context(
    viewport=viewport,
    user_agent=random.choice(user_agents),
    timezone_id=random.choice(timezones),
    locale='en-US',
    permissions=['geolocation'],
    geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
    color_scheme='light',
    device_scale_factor=1,
)
```

---

### Phase 4: CAPTCHA Solving (Required for Some Sites)

**Problem:** Sites like Costco may show CAPTCHA challenges.

**Solutions:**

#### Option A: 2Captcha (Recommended)
- **Cost:** ~$3 per 1000 CAPTCHAs
- Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile
- 95%+ success rate
- 10-30 second solve time

**Integration:**
```python
from twocaptcha import TwoCaptcha

solver = TwoCaptcha('YOUR_API_KEY')

# For reCAPTCHA
result = solver.recaptcha(
    sitekey='6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-',
    url='https://www.costco.com'
)

# Inject solution
await page.evaluate(f'document.getElementById("g-recaptcha-response").innerHTML="{result["code"]}";')
```

#### Option B: Anti-Captcha
- Similar pricing and features
- Slightly faster (8-25 seconds)
- Good alternative if 2Captcha has issues

#### Option C: CapSolver
- AI-powered solving
- Best for difficult CAPTCHAs
- More expensive (~$5 per 1000)

**Recommendation:** Start with 2Captcha (cheapest and reliable).

---

### Phase 5: Request Rate Limiting & Session Management

**1. Smart Rate Limiting**

```python
import random
import time

class RateLimiter:
    def __init__(self):
        self.last_request = 0
        self.requests_this_minute = 0

    async def wait(self):
        # Random delay between 2-8 seconds (human-like)
        delay = random.uniform(2, 8)

        # Add extra delay every 10 requests (simulate user behavior)
        if self.requests_this_minute % 10 == 0:
            delay += random.uniform(30, 120)  # Take a "break"

        await asyncio.sleep(delay)
        self.requests_this_minute += 1
```

**2. Session Persistence**

```python
# Save cookies and reuse sessions (like a real user)
await context.storage_state(path='session.json')

# Later, restore session
context = await browser.new_context(
    storage_state='session.json'
)
```

**3. Distributed Requests**

- Spread requests across multiple IPs
- Use different browser instances
- Vary request patterns

---

### Phase 6: Monitoring & Fallback Strategies

**1. Detection Monitoring**

```python
async def check_for_blocking(page):
    content = await page.content()

    # Check for common blocking patterns
    blocking_indicators = [
        'access denied',
        'captcha',
        'cloudflare',
        'unusual traffic',
        'please verify',
        'robot',
        'automated'
    ]

    if any(indicator in content.lower() for indicator in blocking_indicators):
        logger.warning("Potential blocking detected", url=page.url)
        return True

    return False
```

**2. Automatic Fallback**

```python
async def scrape_with_fallback(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Try method 1: Stealth browser + residential proxy
            result = await scrape_with_browser(url, proxy='residential')

            if not await check_for_blocking(result):
                return result

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed", error=str(e))

            # Fallback to different approach
            if attempt == 0:
                # Try different proxy
                result = await scrape_with_browser(url, proxy='mobile_residential')
            elif attempt == 1:
                # Add CAPTCHA solving
                result = await scrape_with_captcha_solving(url)
            else:
                # Final attempt: Manual intervention queue
                await queue_for_manual_review(url)

        await asyncio.sleep(60 * (attempt + 1))  # Exponential backoff

    raise ScrapingFailedError("All retry attempts failed")
```

---

## Recommended Implementation Plan

### Week 1: Foundation
1. **Set up Playwright infrastructure**
   - Lambda layer with Chromium
   - Stealth plugin integration
   - Basic fingerprint randomization

2. **Test on moderate difficulty sites**
   - Forever21 (already works)
   - Target
   - Walmart

### Week 2: Advanced Techniques
3. **Integrate residential proxy network**
   - Sign up for Bright Data trial
   - Test proxy rotation
   - Measure success rates

4. **Implement undetection techniques**
   - Advanced fingerprint randomization
   - Behavioral simulation
   - Request timing optimization

### Week 3: CAPTCHA & Hard Targets
5. **Add CAPTCHA solving**
   - 2Captcha integration
   - Automatic CAPTCHA detection
   - Fallback strategies

6. **Test on hard targets**
   - Costco
   - Amazon
   - Nike/Adidas (very difficult)

### Week 4: Production Readiness
7. **Monitoring and optimization**
   - Success rate tracking
   - Cost optimization
   - Performance tuning

8. **Fallback and error handling**
   - Automatic retries
   - Multiple proxy providers
   - Manual review queue

---

## Cost Estimation

### Monthly Costs (Mid-Volume: ~100K pages/month)

| Component | Cost | Notes |
|-----------|------|-------|
| Residential Proxies (Bright Data) | $500 | 20GB bandwidth |
| CAPTCHA Solving (2Captcha) | $100 | ~33K CAPTCHAs |
| AWS Lambda (Browser) | $200 | Increased memory/timeout |
| AWS ECS (Optional) | $300 | If Lambda insufficient |
| **Total** | **$800-1,100/month** | Scales with usage |

### Low Volume (<10K pages/month)
- $100-200/month (mostly proxy costs)

### High Volume (>1M pages/month)
- $3,000-5,000/month
- Consider dedicated infrastructure
- Volume discounts from proxy providers

---

## Competitive Analysis

### What Competitors Use

**ScrapingBee, Oxylabs, Bright Data:**
- Headless browsers (Playwright/Puppeteer)
- Residential proxy networks
- Automatic CAPTCHA solving
- AI-powered undetection
- **Pricing:** $50-500/month for similar volumes

**Why they're ahead:**
- Years of anti-detection R&D
- Large residential proxy networks
- Economies of scale
- Dedicated infrastructure

**How we catch up:**
- Use same technologies (Playwright + proxies)
- Leverage existing CAPTCHA services
- Start with hard targets as differentiator
- Offer better UX/integration

---

## Success Metrics

### Phase 1 Goals (MVP)
- ✅ 80%+ success rate on moderate sites (Target, Walmart)
- ✅ 50%+ success rate on hard sites (Costco, Amazon)
- ✅ <30 second average scrape time
- ✅ CAPTCHA solving when needed

### Phase 2 Goals (Production)
- ✅ 95%+ success rate on moderate sites
- ✅ 80%+ success rate on hard sites
- ✅ <15 second average scrape time
- ✅ Automatic fallback working
- ✅ Cost under $1,000/month for 100K pages

### Phase 3 Goals (Advanced)
- ✅ 98%+ success rate on all public sites
- ✅ Handle rate limiting automatically
- ✅ Session persistence working
- ✅ Sub-10 second scrape time

---

## Technical Risks & Mitigations

### Risk 1: Lambda Cold Starts
**Impact:** 10-30 second delay on first request
**Mitigation:**
- Keep Lambda warm with CloudWatch Events
- Consider ECS for consistent performance
- Batch requests where possible

### Risk 2: Proxy IP Bans
**Impact:** Temporary inability to scrape certain sites
**Mitigation:**
- Multiple proxy providers
- Automatic provider switching
- IP rotation strategies
- Fallback to manual review

### Risk 3: CAPTCHA Cost Explosion
**Impact:** Unexpected $500+ CAPTCHA bills
**Mitigation:**
- Set spending limits on 2Captcha
- Better bot detection avoidance (fewer CAPTCHAs)
- Cache successful sessions
- Rate limiting

### Risk 4: Site Changes
**Impact:** Selectors break, scraping fails
**Mitigation:**
- Monitoring and alerts
- Automatic fallback to visual builder
- Version control for selectors
- Community-maintained templates

---

## Legal & Ethical Considerations

### Legal
- ✅ Scraping public data is generally legal (US case law)
- ❌ Don't bypass authentication/paywalls
- ❌ Respect `robots.txt` (configurable)
- ✅ Use rate limiting to avoid DoS
- ✅ Provide clear terms of service

### Ethical
- ✅ Be respectful of target sites
- ✅ Don't cause harm or outages
- ✅ Cache aggressively to reduce load
- ✅ Provide value to end users
- ❌ Don't scrape personal data without consent

### Terms of Service
- Some sites explicitly prohibit scraping
- Users must agree to use responsibly
- Provide warnings for certain targets
- Consider "use at your own risk" disclaimer

---

## Next Steps

### Immediate (This Week)
1. Research Bright Data trial signup
2. Set up Playwright Lambda layer
3. Implement basic stealth techniques
4. Test on Costco

### Short Term (This Month)
5. Full residential proxy integration
6. CAPTCHA solving implementation
7. Test on 10+ difficult sites
8. Document success rates

### Long Term (Next Quarter)
9. Build monitoring dashboard
10. Optimize costs
11. Add more proxy providers
12. Scale to high volume

---

## References & Resources

### Documentation
- Playwright: https://playwright.dev/python/
- Playwright Stealth: https://github.com/AtuboDad/playwright_stealth
- Undetected ChromeDriver: https://github.com/ultrafunkamsterdam/undetected-chromedriver
- 2Captcha API: https://2captcha.com/2captcha-api

### Proxy Providers
- Bright Data: https://brightdata.com/
- Oxylabs: https://oxylabs.io/
- SmartProxy: https://smartproxy.com/

### Bot Detection Info
- Cloudflare Bot Detection: https://developers.cloudflare.com/bots/
- PerimeterX: https://www.humansecurity.com/products/perimeter-x
- DataDome: https://datadome.co/

### Case Studies
- "Bypassing Cloudflare Bot Protection" (2024)
- "Residential Proxies vs Bot Detection" (2025)
- "CAPTCHA Solving ROI Analysis" (2025)

---

**Last Updated:** 2026-02-01
**Next Review:** When implementation begins
**Owner:** Engineering Team
