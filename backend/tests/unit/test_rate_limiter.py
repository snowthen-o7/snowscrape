"""Unit tests for rate_limiter.DomainRateLimiter.

DomainRateLimiter enforces a minimum delay between requests to the same domain
so scrapes do not hammer a target server or trip its bot protection. It is on
the live scraping path (crawler.py, job_manager.py, tiered_scraper.py all use it)
but had no dedicated coverage. A silent regression here is a reliability/abuse
risk: a broken delay either floods the target (bot bans, IP blocks) or never
returns (hangs the Lambda).

The module's only non-determinism is `time.time()` / `time.sleep()`, so these
tests drive a FakeClock: `time()` returns a controllable instant and `sleep(dt)`
advances it (modelling real wall-clock movement) instead of actually sleeping,
so the suite is fast and deterministic.
"""
import pytest

import rate_limiter
from rate_limiter import DomainRateLimiter, DEFAULT_MIN_DELAY


class FakeClock:
    """A controllable stand-in for the `time` module used by rate_limiter.

    `time()` returns `now`; `sleep(dt)` advances `now` by `dt` and records the
    requested duration, so a test can both assert what was slept and observe the
    post-sleep instant the limiter records.
    """

    def __init__(self, start: float = 1000.0):
        self.now = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    # NOTE: the fixture below patches `rate_limiter.time.time/.sleep`. The module
    # does `import time` and calls `time.time()` / `time.sleep()` by attribute, so
    # this is the reference the source actually uses. If rate_limiter is ever
    # refactored to `from time import time, sleep`, update the patch targets to
    # match or these tests would silently run against the real clock.

    def advance(self, seconds: float) -> None:
        """Move wall-clock forward WITHOUT going through the limiter's sleep."""
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(rate_limiter.time, "time", c.time)
    monkeypatch.setattr(rate_limiter.time, "sleep", c.sleep)
    return c


class TestInit:
    def test_default_min_delay(self):
        assert DomainRateLimiter().min_delay == DEFAULT_MIN_DELAY == 1.0

    def test_custom_min_delay_stored(self):
        assert DomainRateLimiter(min_delay=2.5).min_delay == 2.5

    def test_zero_min_delay_allowed(self):
        # zero is a valid "no rate limiting" configuration, not an error
        assert DomainRateLimiter(min_delay=0).min_delay == 0

    def test_negative_min_delay_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            DomainRateLimiter(min_delay=-0.1)

    def test_fresh_limiter_has_no_tracked_domains(self):
        assert len(DomainRateLimiter()._last_request_time) == 0


class TestGetDomain:
    def test_https_url(self):
        assert DomainRateLimiter.get_domain("https://example.com/path?q=1") == "example.com"

    def test_http_url(self):
        assert DomainRateLimiter.get_domain("http://example.com/a/b") == "example.com"

    def test_subdomain_preserved(self):
        assert DomainRateLimiter.get_domain("https://api.shop.example.com/x") == "api.shop.example.com"

    def test_port_included_in_domain(self):
        # netloc includes the port, so :8080 vs :443 are distinct "domains"
        assert DomainRateLimiter.get_domain("http://example.com:8080/x") == "example.com:8080"

    def test_userinfo_included_in_netloc(self):
        assert DomainRateLimiter.get_domain("http://user:pass@host.com/x") == "user:pass@host.com"

    def test_path_only_has_no_domain(self):
        # no scheme/host -> urlparse treats the whole thing as a path, netloc == ""
        assert DomainRateLimiter.get_domain("/just/a/path") == ""

    def test_schemeless_host_is_not_parsed_as_netloc(self):
        # a classic gotcha: without a scheme, "example.com/x" is a path, not a host
        assert DomainRateLimiter.get_domain("example.com/path") == ""

    def test_empty_string(self):
        assert DomainRateLimiter.get_domain("") == ""


class TestWaitIfNeededDisabled:
    """A disabled limiter (min_delay <= 0) returns 0, never sleeps, and records
    no per-domain state.

    The first two tests pin the observable disabled-output (return 0, no sleep);
    note the fall-through path would also return 0 at min_delay==0, so the
    DISTINGUISHING pin for the `min_delay <= 0` short-circuit itself is
    test_zero_delay_records_no_domain_state (without the early return, the
    fall-through reaches `_last_request_time[domain] = time.time()` and records
    state).
    """

    def test_zero_delay_returns_zero(self, clock):
        limiter = DomainRateLimiter(min_delay=0)
        assert limiter.wait_if_needed("https://example.com/a") == 0.0

    def test_zero_delay_never_sleeps(self, clock):
        limiter = DomainRateLimiter(min_delay=0)
        limiter.wait_if_needed("https://example.com/a")
        assert clock.sleeps == []

    def test_zero_delay_records_no_domain_state(self, clock):
        # the early return happens BEFORE the defaultdict is touched, so a
        # disabled limiter never accumulates per-domain timestamps. This is the
        # test that genuinely fails if the `min_delay <= 0` short-circuit is
        # removed (the fall-through would record time.time() for the domain).
        limiter = DomainRateLimiter(min_delay=0)
        limiter.wait_if_needed("https://example.com/a")
        assert len(limiter._last_request_time) == 0


class TestWaitIfNeededFirstRequest:
    def test_first_request_to_domain_does_not_wait(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        # the no-wait here is the real contract: an unseen domain's
        # last_request_time defaults to 0.0, so elapsed == now (>> min_delay).
        # Assert that defaultdict default explicitly so the test does not silently
        # depend on the FakeClock start happening to exceed min_delay.
        assert limiter._last_request_time["example.com"] == 0.0
        limiter._last_request_time.clear()  # the read above created the key; undo it
        assert limiter.wait_if_needed("https://example.com/a") == 0.0
        assert clock.sleeps == []

    def test_first_request_records_current_time(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://example.com/a")
        assert limiter._last_request_time["example.com"] == clock.now == 1000.0


class TestWaitIfNeededThrottling:
    def test_second_request_within_window_sleeps_remaining(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://example.com/a")  # records t=1000.0
        clock.advance(0.3)  # 0.3s of real work happens
        waited = limiter.wait_if_needed("https://example.com/b")
        # only the remaining 0.7s should be slept
        assert waited == pytest.approx(0.7)
        assert clock.sleeps == [pytest.approx(0.7)]

    def test_after_sleep_records_post_wait_instant(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://example.com/a")  # t=1000.0
        clock.advance(0.3)  # now 1000.3
        limiter.wait_if_needed("https://example.com/b")  # sleeps 0.7 -> 1001.0
        assert limiter._last_request_time["example.com"] == pytest.approx(1001.0)

    def test_request_after_window_elapsed_does_not_wait(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://example.com/a")  # t=1000.0
        clock.advance(1.5)  # more than min_delay has passed
        assert limiter.wait_if_needed("https://example.com/b") == 0.0
        assert clock.sleeps == []

    def test_request_exactly_at_window_boundary_does_not_wait(self, clock):
        # elapsed == min_delay is NOT < min_delay, so the boundary does not sleep
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://example.com/a")  # t=1000.0
        clock.advance(1.0)
        assert limiter.wait_if_needed("https://example.com/b") == 0.0
        assert clock.sleeps == []

    def test_back_to_back_requests_each_sleep_full_delay(self, clock):
        limiter = DomainRateLimiter(min_delay=2.0)
        limiter.wait_if_needed("https://example.com/a")  # t=1000.0, no wait
        w2 = limiter.wait_if_needed("https://example.com/b")  # elapsed 0 -> wait 2.0
        w3 = limiter.wait_if_needed("https://example.com/c")  # elapsed 0 -> wait 2.0
        assert w2 == pytest.approx(2.0)
        assert w3 == pytest.approx(2.0)
        assert clock.sleeps == [pytest.approx(2.0), pytest.approx(2.0)]


class TestWaitIfNeededPerDomain:
    def test_different_domains_tracked_independently(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/x")  # records a.com
        # an immediate request to a DIFFERENT domain must not wait
        assert limiter.wait_if_needed("https://b.com/y") == 0.0
        assert clock.sleeps == []
        assert set(limiter._last_request_time) == {"a.com", "b.com"}

    def test_same_domain_different_paths_share_a_limit(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/page1")
        waited = limiter.wait_if_needed("https://a.com/page2")
        # same netloc -> throttled despite the different path
        assert waited == pytest.approx(1.0)

    def test_port_makes_distinct_domains(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("http://a.com:80/x")
        # different port -> different netloc -> not throttled
        assert limiter.wait_if_needed("http://a.com:81/x") == 0.0


class TestReset:
    def test_reset_single_domain_clears_only_that_domain(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/x")
        limiter.wait_if_needed("https://b.com/y")
        limiter.reset("a.com")
        assert "a.com" not in limiter._last_request_time
        assert "b.com" in limiter._last_request_time

    def test_reset_unknown_domain_is_noop(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/x")
        limiter.reset("never-seen.com")  # pop(..., None) -> no KeyError
        assert "a.com" in limiter._last_request_time

    def test_reset_all_clears_every_domain(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/x")
        limiter.wait_if_needed("https://b.com/y")
        limiter.reset()
        assert len(limiter._last_request_time) == 0

    def test_after_reset_domain_is_treated_as_first_request(self, clock):
        limiter = DomainRateLimiter(min_delay=1.0)
        limiter.wait_if_needed("https://a.com/x")  # records a.com
        limiter.reset("a.com")
        # next request behaves like a fresh domain: no throttle
        assert limiter.wait_if_needed("https://a.com/x") == 0.0
        assert clock.sleeps == []
