"""Unit tests for tiered_scraper: blocking detection, Tier 1/2, and escalation.

`tiered_scraper` is the live scrape engine: every URL a job crawls goes through
`smart_scrape`, which starts at the cheapest tier and escalates on blocking. The
Firecrawl tiers (3/4) already have coverage in `test_firecrawl_tiers.py`; this
file pins the parts that had ZERO dedicated coverage and are correctness/abuse/
cost boundaries:

  * `detect_blocking` -- the heuristic that decides "we were blocked." A false
    negative scrapes a challenge page as if it were real data (silent garbage);
    a false positive needlessly escalates to a 50x-more-expensive tier.
  * `scrape_tier_1` -- the default cheap path (requests + BeautifulSoup), incl.
    the SSRF pre-check and blocking-raises contract.
  * `scrape_tier_2` -- IP-rotation proxy resolution (provided config > env var >
    AWS pool > NotImplementedError) and the `verify=False` proxy contract.
  * `smart_scrape` -- the escalation state machine (escalate on blocking, do NOT
    escalate on NotImplementedError, escalate on generic error, max-tier cap,
    auto_escalate=False), the live cost/reliability decision.
  * `get_tier_info` / `estimate_cost` -- the pure cost helpers.

These are characterization tests (no source change): they pin CURRENT behavior so
a future refactor that changes it fails loudly.

`scrape_tier_2`'s third proxy branch imports `proxy_manager`, which builds boto3
clients at import time, so AWS region + dummy creds are set with `setdefault`
BEFORE importing the module under test (mirrors test_proxy_manager). Network is
never reached: `requests.get`/`post` and `validate_scrape_url` are always patched.
"""
import asyncio
import os

# proxy_manager (imported lazily inside scrape_tier_2's AWS-pool branch) constructs
# boto3 clients at import time, which needs a region and (lazily) credentials.
# setdefault never clobbers a real ambient AWS config; it only guarantees import
# succeeds in a bare test environment.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import pytest

import tiered_scraper
from tiered_scraper import (
    BlockingDetectionError,
    detect_blocking,
    scrape_tier_1,
    scrape_tier_2,
    smart_scrape,
    get_tier_info,
    estimate_cost,
    TIER_INFO,
)
from validators import ValidationError


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeResponse:
    """A minimal stand-in for requests.Response.

    detect_blocking reads `.status_code` and `.text`; the tier functions also read
    `.content` (BeautifulSoup parses it), `.url`, and `.headers`. A real fake (not
    a MagicMock) is used deliberately: MagicMock would make `.text` a non-string
    Mock and break `text.lower()` inside detect_blocking.
    """

    def __init__(self, status_code=200, text="", content=None, url="https://example.com", headers=None):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.url = url
        self.headers = headers or {}


def _ok_html(title="Test", body="<h1>Real content</h1>" + ("<p>filler</p>" * 30)):
    """A clean, non-minimal HTML page that should NOT trip blocking detection."""
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"


# --------------------------------------------------------------------------- #
# detect_blocking
# --------------------------------------------------------------------------- #
class TestDetectBlocking:
    def test_clean_200_page_not_blocked(self):
        resp = FakeResponse(status_code=200, text=_ok_html())
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is False
        assert indicators == []

    @pytest.mark.parametrize(
        "status,indicator",
        [
            (403, "403_forbidden"),
            (429, "429_rate_limited"),
            (503, "503_service_unavailable"),
        ],
    )
    def test_blocking_status_codes(self, status, indicator):
        # Long clean body so the <200-char 'minimal_content' rule does not also fire.
        resp = FakeResponse(status_code=status, text=_ok_html())
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is True
        assert indicators == [indicator]

    def test_other_4xx_5xx_status_not_an_indicator_on_its_own(self):
        # 404/500 are NOT in the status whitelist; with substantial clean content
        # there is no indicator at all.
        for status in (404, 500):
            resp = FakeResponse(status_code=status, text=_ok_html())
            is_blocked, indicators = detect_blocking(resp)
            assert is_blocked is False, status
            assert indicators == [], status

    @pytest.mark.parametrize(
        "needle,indicator",
        [
            ("just a moment...", "cloudflare_challenge"),
            ("Checking your browser", "cloudflare_challenge"),
            ("cf-browser-verification", "cloudflare_verification"),
            ("Access Denied", "access_denied"),
            ("verify you are human", "human_verification"),
            ("unusual traffic from your computer network", "unusual_traffic"),
            ("datadome", "datadome_challenge"),
            ("net::ERR_TIMED_OUT", "browser_connection_error"),
            ('class="neterror"', "browser_error_page"),
        ],
    )
    def test_content_challenge_patterns(self, needle, indicator):
        # Embed the needle in an otherwise-long 200 page so only the content rule
        # (not status / minimal-content) explains the indicator.
        resp = FakeResponse(status_code=200, text=_ok_html(body=needle + ("<p>x</p>" * 40)))
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is True
        assert indicator in indicators

    def test_pattern_match_is_case_insensitive(self):
        # Patterns are matched against text.lower(), so SHOUTING still trips.
        resp = FakeResponse(status_code=200, text="ACCESS DENIED " + ("padding " * 40))
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is True
        assert "access_denied" in indicators

    def test_content_arg_overrides_response_text(self):
        # When `content` is passed it is checked INSTEAD of response.text. A clean
        # response with a blocked rendered body is blocked...
        resp = FakeResponse(status_code=200, text=_ok_html())
        is_blocked, indicators = detect_blocking(resp, content="please complete the security check " + ("y" * 200))
        assert is_blocked is True
        assert "security_check" in indicators

    def test_content_arg_clean_ignores_dirty_response_text(self):
        # ...and conversely a clean `content` arg is trusted over a dirty .text.
        resp = FakeResponse(status_code=200, text="access denied")
        is_blocked, indicators = detect_blocking(resp, content=_ok_html())
        assert is_blocked is False
        assert indicators == []

    def test_minimal_content_only_flagged_with_status_or_other_indicator(self):
        # A short clean 200 body alone is NOT minimal_content (avoids false positives
        # on legitimately tiny pages).
        resp_ok = FakeResponse(status_code=200, text="tiny clean page")
        is_blocked, indicators = detect_blocking(resp_ok)
        assert is_blocked is False
        assert indicators == []

        # The same short body at a >=400 status DOES add minimal_content.
        resp_bad = FakeResponse(status_code=404, text="tiny error page")
        is_blocked, indicators = detect_blocking(resp_bad)
        assert is_blocked is True
        assert indicators == ["minimal_content"]

    def test_indicators_accumulate(self):
        # A 403 whose short body also says "access denied" yields all three:
        # status + content pattern + minimal_content.
        resp = FakeResponse(status_code=403, text="access denied")
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is True
        assert "403_forbidden" in indicators
        assert "access_denied" in indicators
        assert "minimal_content" in indicators

    def test_empty_text_and_clean_status_not_blocked(self):
        # No text to check + a non-blocking status -> nothing fires.
        resp = FakeResponse(status_code=200, text="")
        is_blocked, indicators = detect_blocking(resp)
        assert is_blocked is False
        assert indicators == []


# --------------------------------------------------------------------------- #
# scrape_tier_1
# --------------------------------------------------------------------------- #
class TestScrapeTier1:
    @pytest.fixture(autouse=True)
    def _patch(self, monkeypatch):
        # Always neutralize the SSRF check and the network for tier-1 tests; each
        # test overrides as needed.
        monkeypatch.setattr(tiered_scraper, "validate_scrape_url", lambda url: url)

    def test_success_returns_tier1_metadata(self, monkeypatch):
        captured = {}

        def fake_get(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return FakeResponse(status_code=200, text=_ok_html(title="Hello"))

        monkeypatch.setattr(tiered_scraper.requests, "get", fake_get)

        result = scrape_tier_1("https://example.com/page", timeout=12)

        assert result["tier_used"] == 1
        assert result["tier_name"] == "Lightweight"
        assert result["cost"] == 0.0001
        assert result["status_code"] == 200
        assert result["soup"].title.string == "Hello"
        assert result["text"].startswith("<html>")
        # The browser-like User-Agent header and the caller timeout are forwarded.
        assert "User-Agent" in captured["kwargs"]["headers"]
        assert captured["kwargs"]["timeout"] == 12
        assert captured["kwargs"]["allow_redirects"] is True
        assert captured["url"] == "https://example.com/page"

    def test_ssrf_failure_raises_url_required(self, monkeypatch):
        def boom(url):
            raise ValidationError("private IP blocked")

        monkeypatch.setattr(tiered_scraper, "validate_scrape_url", boom)
        # Network must never be touched if validation fails.
        monkeypatch.setattr(
            tiered_scraper.requests,
            "get",
            lambda *a, **k: pytest.fail("requests.get called despite SSRF failure"),
        )

        import requests
        with pytest.raises(requests.exceptions.URLRequired, match="SSRF protection"):
            scrape_tier_1("http://169.254.169.254/")

    def test_blocking_raises_blocking_detection_error_tier1(self, monkeypatch):
        monkeypatch.setattr(
            tiered_scraper.requests,
            "get",
            lambda *a, **k: FakeResponse(status_code=403, text=_ok_html()),
        )
        with pytest.raises(BlockingDetectionError) as exc:
            scrape_tier_1("https://example.com")
        assert exc.value.tier_used == 1
        assert "403_forbidden" in exc.value.indicators


# --------------------------------------------------------------------------- #
# scrape_tier_2 (proxy resolution)
# --------------------------------------------------------------------------- #
class TestScrapeTier2:
    @pytest.fixture(autouse=True)
    def _patch(self, monkeypatch):
        monkeypatch.setattr(tiered_scraper, "validate_scrape_url", lambda url: url)
        # Ensure no ambient residential proxy leaks into the resolution order.
        monkeypatch.delenv("RESIDENTIAL_PROXY_URL", raising=False)

    def _record_get(self, monkeypatch):
        captured = {}

        def fake_get(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return FakeResponse(status_code=200, text=_ok_html())

        monkeypatch.setattr(tiered_scraper.requests, "get", fake_get)
        return captured

    def test_uses_provided_proxy_config_https_first(self, monkeypatch):
        captured = self._record_get(monkeypatch)
        result = scrape_tier_2(
            "https://example.com",
            proxy_config={"http": "http://h:1", "https": "http://s:2"},
        )
        assert result["tier_used"] == 2
        assert result["tier_name"] == "IP Rotation"
        assert result["cost"] == 0.005
        # https is preferred over http; both proxy slots get that URL.
        assert captured["kwargs"]["proxies"] == {"http": "http://s:2", "https": "http://s:2"}
        # Proxy SSL interception requires verify=False; redirects are followed.
        assert captured["kwargs"]["verify"] is False
        assert captured["kwargs"]["allow_redirects"] is True

    def test_falls_back_to_http_proxy_when_no_https(self, monkeypatch):
        captured = self._record_get(monkeypatch)
        scrape_tier_2("https://example.com", proxy_config={"http": "http://only-http:1"})
        # Both proxy slots get the single available URL.
        assert captured["kwargs"]["proxies"] == {
            "http": "http://only-http:1",
            "https": "http://only-http:1",
        }

    def test_uses_residential_proxy_env_var(self, monkeypatch):
        monkeypatch.setenv("RESIDENTIAL_PROXY_URL", "http://res-proxy:8080")
        captured = self._record_get(monkeypatch)
        scrape_tier_2("https://example.com")
        assert captured["kwargs"]["proxies"] == {
            "http": "http://res-proxy:8080",
            "https": "http://res-proxy:8080",
        }

    def test_uses_aws_proxy_pool_when_no_config_or_env(self, monkeypatch):
        captured = self._record_get(monkeypatch)
        # Capture the config OUTSIDE get_proxy_url: asserting inside it would be
        # swallowed by the source's `except Exception` and surface as a misleading
        # NotImplementedError instead of a clear assertion failure.
        passed_config = {}

        class FakeManager:
            def get_proxy_url(self, config):
                passed_config.update(config)
                return "http://aws-pool-proxy:3128"

        monkeypatch.setattr("proxy_manager.get_proxy_manager", lambda: FakeManager())
        scrape_tier_2("https://example.com")
        assert captured["kwargs"]["proxies"]["http"] == "http://aws-pool-proxy:3128"
        # The tier requests an enabled pool, geo 'any', random rotation, no direct fallback.
        assert passed_config["enabled"] is True
        assert passed_config["geo_targeting"] == "any"
        assert passed_config["rotation_strategy"] == "random"
        assert passed_config["fallback_to_direct"] is False

    def test_no_proxy_available_raises_not_implemented(self, monkeypatch):
        # AWS pool unavailable -> the except-branch swallows it, proxy_url stays
        # None, and the helpful NotImplementedError is raised (never escalated).
        def boom():
            raise RuntimeError("secretsmanager unavailable")

        monkeypatch.setattr("proxy_manager.get_proxy_manager", boom)
        monkeypatch.setattr(
            tiered_scraper.requests,
            "get",
            lambda *a, **k: pytest.fail("requests.get called with no proxy"),
        )
        with pytest.raises(NotImplementedError, match="requires proxy configuration"):
            scrape_tier_2("https://example.com")

    def test_blocking_with_proxy_raises_tier2(self, monkeypatch):
        monkeypatch.setattr(
            tiered_scraper.requests,
            "get",
            lambda *a, **k: FakeResponse(status_code=429, text=_ok_html()),
        )
        with pytest.raises(BlockingDetectionError) as exc:
            scrape_tier_2("https://example.com", proxy_config={"https": "http://p:1"})
        assert exc.value.tier_used == 2
        assert "429_rate_limited" in exc.value.indicators


# --------------------------------------------------------------------------- #
# smart_scrape (escalation state machine)
# --------------------------------------------------------------------------- #
def _success(tier):
    return {"tier_used": tier, "tier_name": TIER_INFO[tier]["name"], "cost": TIER_INFO[tier]["cost_per_page"]}


def _patch_tiers(monkeypatch, behaviors):
    """behaviors: dict tier -> callable(url, **kwargs) OR an Exception instance to raise."""
    for tier, behavior in behaviors.items():
        if isinstance(behavior, BaseException):
            def make(exc):
                def fn(url, **kwargs):
                    raise exc
                return fn
            monkeypatch.setattr(tiered_scraper, f"scrape_tier_{tier}", make(behavior))
        else:
            monkeypatch.setattr(tiered_scraper, f"scrape_tier_{tier}", behavior)


class TestSmartScrape:
    def test_returns_first_tier_on_success(self, monkeypatch):
        _patch_tiers(monkeypatch, {1: lambda url, **k: _success(1)})
        result, tier, log = asyncio.run(smart_scrape("https://example.com"))
        assert tier == 1
        assert result["tier_used"] == 1
        assert any("Success with Tier 1" in line for line in log)

    def test_escalates_past_blocking_to_next_tier(self, monkeypatch):
        _patch_tiers(
            monkeypatch,
            {
                1: BlockingDetectionError("blocked", tier_used=1, indicators=["403_forbidden"]),
                2: lambda url, **k: _success(2),
            },
        )
        result, tier, log = asyncio.run(smart_scrape("https://example.com"))
        assert tier == 2
        assert any("Escalating to Tier 2" in line for line in log)
        assert any("Tier 1 blocked" in line for line in log)

    def test_no_escalation_when_auto_escalate_false(self, monkeypatch):
        _patch_tiers(
            monkeypatch,
            {1: BlockingDetectionError("blocked", tier_used=1, indicators=["x"])},
        )
        with pytest.raises(Exception, match="Scraping failed at Tier 1"):
            asyncio.run(smart_scrape("https://example.com", auto_escalate=False))

    def test_blocking_at_max_tier_raises(self, monkeypatch):
        _patch_tiers(
            monkeypatch,
            {1: BlockingDetectionError("blocked", tier_used=1, indicators=["x"])},
        )
        # max_tier == min_tier == 1, so there is nowhere to escalate.
        with pytest.raises(Exception, match="Scraping failed at Tier 1"):
            asyncio.run(smart_scrape("https://example.com", max_tier=1))

    def test_not_implemented_does_not_escalate(self, monkeypatch):
        # A NotImplementedError is a "this tier can't run here" signal: it surfaces a
        # helpful message and must NOT silently fall through to a pricier tier.
        tier3_called = {"hit": False}

        def tier3(url, **kwargs):
            tier3_called["hit"] = True
            return _success(3)

        _patch_tiers(
            monkeypatch,
            {
                2: NotImplementedError("Set RESIDENTIAL_PROXY_URL"),
                3: tier3,
            },
        )
        with pytest.raises(Exception, match="not yet implemented") as exc:
            asyncio.run(smart_scrape("https://example.com", min_tier=2, max_tier=4))
        assert "Week 1" in str(exc.value)  # tier-2-specific guidance
        assert tier3_called["hit"] is False

    def test_generic_error_escalates_then_succeeds(self, monkeypatch):
        _patch_tiers(
            monkeypatch,
            {
                1: RuntimeError("flaky network"),
                2: lambda url, **k: _success(2),
            },
        )
        result, tier, log = asyncio.run(smart_scrape("https://example.com"))
        assert tier == 2
        assert any("Escalating to Tier 2 after error" in line for line in log)

    def test_generic_error_at_max_tier_reraises(self, monkeypatch):
        _patch_tiers(monkeypatch, {1: RuntimeError("boom")})
        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(smart_scrape("https://example.com", max_tier=1))

    def test_respects_min_tier_start(self, monkeypatch):
        # Starting at min_tier=3 must not invoke the cheaper tiers.
        tier1_called = {"hit": False}

        def tier1(url, **kwargs):
            tier1_called["hit"] = True
            return _success(1)

        _patch_tiers(monkeypatch, {1: tier1, 3: lambda url, **k: _success(3)})
        result, tier, log = asyncio.run(smart_scrape("https://example.com", min_tier=3))
        assert tier == 3
        assert tier1_called["hit"] is False


# --------------------------------------------------------------------------- #
# Pure helpers: get_tier_info / estimate_cost / TIER_INFO
# --------------------------------------------------------------------------- #
class TestTierCostHelpers:
    def test_get_tier_info_known_tier(self):
        info = get_tier_info(1)
        assert info["name"] == "Lightweight"
        assert info["cost_per_page"] == 0.0001

    def test_get_tier_info_unknown_tier_returns_empty(self):
        assert get_tier_info(99) == {}

    def test_estimate_cost_known_tier(self):
        # Tier 2 is $0.005/page.
        assert estimate_cost(2, 100) == pytest.approx(0.5)
        assert estimate_cost(4, 10) == pytest.approx(0.5)

    def test_estimate_cost_zero_pages(self):
        assert estimate_cost(1, 0) == 0

    def test_estimate_cost_unknown_tier_is_zero(self):
        # Unknown tier -> cost_per_page defaults to 0, so any volume costs 0.
        assert estimate_cost(99, 1000) == 0

    def test_tier_info_tier1_and_tier2_constants(self):
        assert TIER_INFO[1]["name"] == "Lightweight"
        assert TIER_INFO[1]["cost_per_page"] == 0.0001
        assert TIER_INFO[2]["name"] == "IP Rotation"
        assert TIER_INFO[2]["cost_per_page"] == 0.005


# --------------------------------------------------------------------------- #
# BlockingDetectionError carries the escalation contract
# --------------------------------------------------------------------------- #
class TestBlockingDetectionError:
    def test_carries_tier_and_indicators(self):
        err = BlockingDetectionError("blocked", tier_used=3, indicators=["a", "b"])
        assert str(err) == "blocked"
        assert err.tier_used == 3
        assert err.indicators == ["a", "b"]
