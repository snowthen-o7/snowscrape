"""Unit tests for proxy_manager.AWSProxyManager.

AWSProxyManager selects, rotates, and tracks the EC2/Squid proxy pool used by the
4-tier scraper for IP-blocked targets (Tier 2). It is on the live scrape path and
is the abuse/reliability boundary for outbound traffic: a silent regression here
either routes scrapes through unhealthy/wrong-geo proxies (bans, blocked jobs) or
leaks proxy credentials into logs. The module had ZERO dedicated coverage.

These are characterization tests (no source change): they pin the CURRENT behavior
so a future refactor that changes it fails loudly.

The module builds its boto3 clients (secretsmanager / dynamodb / cloudwatch) at
IMPORT time, so AWS_DEFAULT_REGION + dummy creds are set with setdefault BEFORE the
import below (matching how the firecrawl tests defer-import region-dependent code).
The tests then inject deterministic fakes for those clients / the DynamoDB table
rather than reaching AWS, in the same spirit as test_rate_limiter's FakeClock.
"""
import json
import os

# Module-level boto3 clients are constructed when proxy_manager is imported, which
# needs a region and (lazily) credentials. setdefault never clobbers a real ambient
# AWS config; it only guarantees import succeeds in a bare test environment.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

import pytest

import proxy_manager
from proxy_manager import AWSProxyManager, get_proxy_manager


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeSecrets:
    """Stand-in for the module-level secretsmanager client.

    Records call count so a test can prove the 5-minute cache short-circuits a
    second fetch. `raises` makes get_secret_value blow up to exercise the
    error-fallback path.
    """

    def __init__(self, proxies=None, raises=False):
        self._payload = {"proxies": proxies if proxies is not None else []}
        self.raises = raises
        self.calls = 0

    def get_secret_value(self, SecretId=None):
        self.calls += 1
        if self.raises:
            raise RuntimeError("secretsmanager unavailable")
        return {"SecretString": json.dumps(self._payload)}


class FakeTable:
    """Minimal DynamoDB Table double recording writes and serving canned reads."""

    def __init__(self, items=None, get_item_map=None,
                 get_item_error=False, update_error=False, scan_error=False):
        self._items = items or []
        self._get_item_map = get_item_map or {}  # proxy_id -> request_count
        self.get_item_error = get_item_error
        self.update_error = update_error
        self.scan_error = scan_error
        self.update_calls = []  # list of kwargs dicts

    def get_item(self, Key=None):
        if self.get_item_error:
            raise RuntimeError("get_item failed")
        proxy_id = Key["proxy_id"]
        if proxy_id in self._get_item_map:
            return {"Item": {"proxy_id": proxy_id,
                             "request_count": self._get_item_map[proxy_id]}}
        return {}  # no Item key -> treated as usage 0

    def update_item(self, **kwargs):
        if self.update_error:
            raise RuntimeError("update_item failed")
        self.update_calls.append(kwargs)
        return {}

    def scan(self):
        if self.scan_error:
            raise RuntimeError("scan failed")
        return {"Items": self._items}


class FakeCloudWatch:
    def __init__(self, raises=False):
        self.raises = raises
        self.metric_calls = []

    def put_metric_data(self, **kwargs):
        if self.raises:
            raise RuntimeError("cloudwatch unavailable")
        self.metric_calls.append(kwargs)


@pytest.fixture
def mgr(monkeypatch):
    """A fresh manager with its DynamoDB table swapped for a FakeTable.

    `__init__` assigns self.proxy_table = dynamodb.Table(...), a lazy resource
    handle that does no network I/O on construction, so building the manager is
    safe; individual tests overwrite mgr.proxy_table when they need to control it.
    """
    m = AWSProxyManager()
    m.proxy_table = FakeTable()
    return m


def make_proxy(url, region="us-east-1", status="healthy"):
    return {"url": url, "region": region, "status": status}


# --------------------------------------------------------------------------- #
# _get_proxy_id (static, pure)
# --------------------------------------------------------------------------- #
class TestGetProxyId:
    def test_extracts_ip_from_credentialed_url(self):
        assert AWSProxyManager._get_proxy_id(
            "http://user:pass@1.2.3.4:3128") == "1.2.3.4"

    def test_extracts_ip_with_different_port_and_creds(self):
        assert AWSProxyManager._get_proxy_id(
            "http://u:p@10.0.0.1:8080") == "10.0.0.1"

    def test_no_credentials_falls_back_to_full_url(self):
        # No '@' in the URL -> the regex does not match -> the whole URL is the id.
        url = "http://1.2.3.4:3128"
        assert AWSProxyManager._get_proxy_id(url) == url

    def test_non_ip_host_after_at_falls_back_to_full_url(self):
        # host is a name, not [\d.]+, so '@host.name:' does not match the IP regex.
        url = "http://user:pass@proxy.example.com:3128"
        assert AWSProxyManager._get_proxy_id(url) == url


# --------------------------------------------------------------------------- #
# _mask_proxy_url (static, pure) -- credential-leak boundary
# --------------------------------------------------------------------------- #
class TestMaskProxyUrl:
    def test_masks_password_keeps_username(self):
        assert AWSProxyManager._mask_proxy_url(
            "http://user:secret@1.2.3.4:3128") == "http://user:***@1.2.3.4:3128"

    def test_masked_output_does_not_contain_the_password(self):
        # The security property: the secret must never survive into a log string.
        masked = AWSProxyManager._mask_proxy_url(
            "http://alice:hunter2@9.9.9.9:3128")
        assert "hunter2" not in masked
        assert "alice" in masked  # username is not a secret and is kept for ops

    def test_url_without_credentials_is_unchanged(self):
        url = "http://1.2.3.4:3128"
        assert AWSProxyManager._mask_proxy_url(url) == url


# --------------------------------------------------------------------------- #
# get_proxy_url -- the core selection logic (get_proxy_pool stubbed)
# --------------------------------------------------------------------------- #
class TestGetProxyUrl:
    def test_returns_none_when_config_missing(self, mgr):
        assert mgr.get_proxy_url(None) is None

    def test_returns_none_when_not_enabled(self, mgr, monkeypatch):
        # A disabled config short-circuits BEFORE the pool is ever loaded.
        called = {"pool": False}

        def _pool():
            called["pool"] = True
            return [make_proxy("http://u:p@1.1.1.1:3128")]

        monkeypatch.setattr(mgr, "get_proxy_pool", _pool)
        assert mgr.get_proxy_url({"enabled": False}) is None
        assert called["pool"] is False

    def test_returns_none_when_pool_empty(self, mgr, monkeypatch):
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: [])
        assert mgr.get_proxy_url({"enabled": True}) is None

    def test_any_geo_keeps_only_healthy(self, mgr, monkeypatch):
        pool = [
            make_proxy("http://u:p@1.1.1.1:3128", status="healthy"),
            make_proxy("http://u:p@2.2.2.2:3128", status="unhealthy"),
        ]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        # rotation 'first' (the else branch) makes selection deterministic: the
        # only healthy proxy must be the one returned.
        url = mgr.get_proxy_url({"enabled": True, "geo_targeting": "any",
                                 "rotation_strategy": "first"})
        assert url == "http://u:p@1.1.1.1:3128"

    def test_geo_filter_requires_both_region_and_healthy(self, mgr, monkeypatch):
        pool = [
            make_proxy("http://u:p@1.1.1.1:3128", region="us-east-1", status="healthy"),
            make_proxy("http://u:p@2.2.2.2:3128", region="eu-west-1", status="healthy"),
            make_proxy("http://u:p@3.3.3.3:3128", region="us-west-2", status="unhealthy"),
        ]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        # geo 'us' admits us-east-1 / us-west-2 only, AND status must be healthy,
        # so the eu proxy (wrong region) and the us-west-2 proxy (unhealthy) drop.
        url = mgr.get_proxy_url({"enabled": True, "geo_targeting": "us",
                                 "rotation_strategy": "first"})
        assert url == "http://u:p@1.1.1.1:3128"

    def test_no_match_with_fallback_returns_none(self, mgr, monkeypatch):
        pool = [make_proxy("http://u:p@2.2.2.2:3128", region="eu-west-1")]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        # geo 'us' matches nothing; fallback_to_direct defaults True -> None.
        assert mgr.get_proxy_url(
            {"enabled": True, "geo_targeting": "us"}) is None

    def test_no_match_without_fallback_raises(self, mgr, monkeypatch):
        pool = [make_proxy("http://u:p@2.2.2.2:3128", region="eu-west-1")]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        with pytest.raises(Exception, match="No healthy proxies"):
            mgr.get_proxy_url({"enabled": True, "geo_targeting": "us",
                               "fallback_to_direct": False})

    def test_unknown_geo_matches_nothing_and_falls_back(self, mgr, monkeypatch):
        # region_map.get('antarctica', []) -> [] -> no proxy can match.
        pool = [make_proxy("http://u:p@1.1.1.1:3128", region="us-east-1")]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        assert mgr.get_proxy_url(
            {"enabled": True, "geo_targeting": "antarctica"}) is None

    def test_random_rotation_uses_random_choice(self, mgr, monkeypatch):
        pool = [
            make_proxy("http://u:p@1.1.1.1:3128"),
            make_proxy("http://u:p@2.2.2.2:3128"),
        ]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        captured = {}

        def fake_choice(seq):
            captured["seq"] = seq
            return seq[-1]  # deterministic: pick the last

        monkeypatch.setattr(proxy_manager.random, "choice", fake_choice)
        url = mgr.get_proxy_url({"enabled": True, "geo_targeting": "any",
                                 "rotation_strategy": "random"})
        # random.choice was handed the filtered (healthy) list and its pick is returned.
        assert url == "http://u:p@2.2.2.2:3128"
        assert [p["url"] for p in captured["seq"]] == [
            "http://u:p@1.1.1.1:3128", "http://u:p@2.2.2.2:3128"]

    def test_random_is_the_default_rotation(self, mgr, monkeypatch):
        # No rotation_strategy key -> defaults to 'random' -> random.choice is used.
        pool = [make_proxy("http://u:p@7.7.7.7:3128")]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        used = {"called": False}

        def fake_choice(seq):
            used["called"] = True
            return seq[0]

        monkeypatch.setattr(proxy_manager.random, "choice", fake_choice)
        assert mgr.get_proxy_url(
            {"enabled": True, "geo_targeting": "any"}) == "http://u:p@7.7.7.7:3128"
        assert used["called"] is True

    def test_round_robin_rotation_delegates(self, mgr, monkeypatch):
        pool = [
            make_proxy("http://u:p@1.1.1.1:3128"),
            make_proxy("http://u:p@2.2.2.2:3128"),
        ]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        captured = {}

        def fake_rr(proxies):
            captured["proxies"] = proxies
            return proxies[1]

        monkeypatch.setattr(mgr, "_get_round_robin_proxy", fake_rr)
        url = mgr.get_proxy_url({"enabled": True, "geo_targeting": "any",
                                 "rotation_strategy": "round-robin"})
        assert url == "http://u:p@2.2.2.2:3128"
        # The filtered (healthy) pool is what gets handed to the round-robin picker.
        assert [p["url"] for p in captured["proxies"]] == [
            "http://u:p@1.1.1.1:3128", "http://u:p@2.2.2.2:3128"]

    def test_unknown_rotation_uses_first_proxy(self, mgr, monkeypatch):
        pool = [
            make_proxy("http://u:p@1.1.1.1:3128"),
            make_proxy("http://u:p@2.2.2.2:3128"),
        ]
        monkeypatch.setattr(mgr, "get_proxy_pool", lambda: pool)
        url = mgr.get_proxy_url({"enabled": True, "geo_targeting": "any",
                                 "rotation_strategy": "bogus"})
        assert url == "http://u:p@1.1.1.1:3128"


# --------------------------------------------------------------------------- #
# get_proxy_pool -- Secrets Manager fetch, caching, error fallback
# --------------------------------------------------------------------------- #
class TestGetProxyPool:
    def test_fetches_and_returns_proxies(self, mgr, monkeypatch):
        proxies = [make_proxy("http://u:p@1.1.1.1:3128")]
        fake = FakeSecrets(proxies=proxies)
        monkeypatch.setattr(proxy_manager, "secrets_client", fake)
        assert mgr.get_proxy_pool() == proxies
        assert fake.calls == 1

    def test_caches_within_ttl(self, mgr, monkeypatch):
        fake = FakeSecrets(proxies=[make_proxy("http://u:p@1.1.1.1:3128")])
        monkeypatch.setattr(proxy_manager, "secrets_client", fake)
        first = mgr.get_proxy_pool()
        second = mgr.get_proxy_pool()
        # Second call inside the 5-minute window is served from cache: no re-fetch.
        assert first == second
        assert fake.calls == 1

    def test_zero_ttl_forces_refetch(self, mgr, monkeypatch):
        # A NON-EMPTY pool is load-bearing here: the cache guard is
        # `if self._proxy_pool and (elapsed) < self._cache_ttl`. With ttl=0 the
        # second clause is what fails, so the proxies must be truthy or the first
        # clause alone would force the refetch and the TTL math would go untested.
        fake = FakeSecrets(proxies=[make_proxy("http://u:p@1.1.1.1:3128")])
        monkeypatch.setattr(proxy_manager, "secrets_client", fake)
        mgr._cache_ttl = 0  # elapsed is never < 0, so the cache never serves
        assert mgr.get_proxy_pool()  # precondition: pool is non-empty (truthy)
        mgr.get_proxy_pool()
        assert fake.calls == 2

    def test_error_with_no_cache_returns_empty(self, mgr, monkeypatch):
        fake = FakeSecrets(raises=True)
        monkeypatch.setattr(proxy_manager, "secrets_client", fake)
        assert mgr.get_proxy_pool() == []

    def test_error_returns_stale_cache_when_present(self, mgr, monkeypatch):
        good = FakeSecrets(proxies=[make_proxy("http://u:p@1.1.1.1:3128")])
        monkeypatch.setattr(proxy_manager, "secrets_client", good)
        mgr._cache_ttl = 0  # force the second call to attempt a re-fetch
        warm = mgr.get_proxy_pool()  # populates cache

        bad = FakeSecrets(raises=True)
        monkeypatch.setattr(proxy_manager, "secrets_client", bad)
        # The re-fetch fails, so the manager serves the previously-cached pool
        # rather than dropping every proxy to [].
        assert mgr.get_proxy_pool() == warm
        # And it genuinely went through the failing fetch (not a silent cache hit),
        # so this still exercises the error-fallback branch it claims to pin.
        assert bad.calls == 1


# --------------------------------------------------------------------------- #
# _get_round_robin_proxy -- lowest-usage selection + random fallback
# --------------------------------------------------------------------------- #
class TestRoundRobin:
    def test_picks_lowest_usage_proxy(self, mgr):
        proxies = [
            make_proxy("http://u:p@1.1.1.1:3128"),
            make_proxy("http://u:p@2.2.2.2:3128"),
            make_proxy("http://u:p@3.3.3.3:3128"),
        ]
        mgr.proxy_table = FakeTable(get_item_map={
            "1.1.1.1": 50, "2.2.2.2": 3, "3.3.3.3": 17})
        chosen = mgr._get_round_robin_proxy(proxies)
        assert chosen["url"] == "http://u:p@2.2.2.2:3128"

    def test_missing_usage_row_counts_as_zero(self, mgr):
        proxies = [
            make_proxy("http://u:p@1.1.1.1:3128"),
            make_proxy("http://u:p@2.2.2.2:3128"),
        ]
        # 1.1.1.1 has a high count; 2.2.2.2 has no row at all -> treated as 0 -> wins.
        mgr.proxy_table = FakeTable(get_item_map={"1.1.1.1": 99})
        chosen = mgr._get_round_robin_proxy(proxies)
        assert chosen["url"] == "http://u:p@2.2.2.2:3128"

    def test_get_item_error_counts_as_zero(self, mgr):
        proxies = [make_proxy("http://u:p@1.1.1.1:3128")]
        # Per-proxy get_item failure is caught and that proxy is scored 0; with a
        # single proxy it is still selectable (no outer fallback to random).
        mgr.proxy_table = FakeTable(get_item_error=True)
        chosen = mgr._get_round_robin_proxy(proxies)
        assert chosen["url"] == "http://u:p@1.1.1.1:3128"

    def test_outer_failure_falls_back_to_random(self, mgr, monkeypatch):
        # A proxy missing 'url' raises KeyError in _get_proxy_id, tripping the
        # OUTER except, which falls back to random.choice over the original list.
        proxies = [{"region": "us-east-1", "status": "healthy"}]  # no 'url'
        sentinel = {"url": "http://sentinel", "region": "x", "status": "healthy"}
        monkeypatch.setattr(proxy_manager.random, "choice", lambda seq: sentinel)
        assert mgr._get_round_robin_proxy(proxies) is sentinel


# --------------------------------------------------------------------------- #
# track_usage -- DynamoDB counters + CloudWatch metrics, errors swallowed
# --------------------------------------------------------------------------- #
class TestTrackUsage:
    def test_success_increments_with_zero_failures(self, mgr, monkeypatch):
        table = FakeTable()
        mgr.proxy_table = table
        cw = FakeCloudWatch()
        monkeypatch.setattr(proxy_manager, "cloudwatch", cw)

        mgr.track_usage("http://u:p@1.2.3.4:3128", success=True, bytes_transferred=2048)

        assert len(table.update_calls) == 1
        call = table.update_calls[0]
        assert call["Key"] == {"proxy_id": "1.2.3.4"}
        vals = call["ExpressionAttributeValues"]
        assert vals[":failed"] == 0          # success -> no failure counted
        assert vals[":bytes"] == 2048
        assert vals[":one"] == 1
        # A successful request emits the SuccessfulRequests metric, not Failed.
        metric_names = {m["MetricName"]
                        for m in cw.metric_calls[0]["MetricData"]}
        assert "SuccessfulRequests" in metric_names
        assert "FailedRequests" not in metric_names

    def test_failure_counts_one_failure_and_failed_metric(self, mgr, monkeypatch):
        table = FakeTable()
        mgr.proxy_table = table
        cw = FakeCloudWatch()
        monkeypatch.setattr(proxy_manager, "cloudwatch", cw)

        mgr.track_usage("http://u:p@1.2.3.4:3128", success=False)

        assert table.update_calls[0]["ExpressionAttributeValues"][":failed"] == 1
        metric_names = {m["MetricName"]
                        for m in cw.metric_calls[0]["MetricData"]}
        assert "FailedRequests" in metric_names
        assert "SuccessfulRequests" not in metric_names

    def test_dynamodb_error_is_swallowed(self, mgr, monkeypatch):
        mgr.proxy_table = FakeTable(update_error=True)
        monkeypatch.setattr(proxy_manager, "cloudwatch", FakeCloudWatch())
        # Tracking is best-effort: a write failure must not propagate to the caller
        # (it would otherwise break the scrape that already succeeded).
        mgr.track_usage("http://u:p@1.2.3.4:3128", success=True)  # no raise


# --------------------------------------------------------------------------- #
# mark_proxy_failed
# --------------------------------------------------------------------------- #
class TestMarkProxyFailed:
    def test_records_failure_fields(self, mgr):
        table = FakeTable()
        mgr.proxy_table = table
        mgr.mark_proxy_failed("http://u:p@5.6.7.8:3128", "connection refused")
        call = table.update_calls[0]
        assert call["Key"] == {"proxy_id": "5.6.7.8"}
        assert call["ExpressionAttributeValues"][":error"] == "connection refused"
        assert call["ExpressionAttributeValues"][":one"] == 1

    def test_error_is_swallowed(self, mgr):
        mgr.proxy_table = FakeTable(update_error=True)
        mgr.mark_proxy_failed("http://u:p@5.6.7.8:3128", "boom")  # no raise


# --------------------------------------------------------------------------- #
# get_proxy_stats
# --------------------------------------------------------------------------- #
class TestGetProxyStats:
    def test_maps_items_with_defaults(self, mgr):
        mgr.proxy_table = FakeTable(items=[
            {"proxy_id": "1.1.1.1", "request_count": 10, "bytes_transferred": 500,
             "failed_requests": 2, "consecutive_failures": 0,
             "last_used": 123, "last_error": None},
            {"proxy_id": "2.2.2.2"},  # sparse row -> defaults fill in
        ])
        stats = mgr.get_proxy_stats()
        assert stats[0]["proxy_id"] == "1.1.1.1"
        assert stats[0]["request_count"] == 10
        # Missing numeric fields default to 0; missing optionals default to None.
        assert stats[1]["request_count"] == 0
        assert stats[1]["bytes_transferred"] == 0
        assert stats[1]["last_used"] is None

    def test_scan_error_returns_empty_list(self, mgr):
        mgr.proxy_table = FakeTable(scan_error=True)
        assert mgr.get_proxy_stats() == []


# --------------------------------------------------------------------------- #
# get_proxy_manager singleton
# --------------------------------------------------------------------------- #
class TestSingleton:
    def test_returns_same_instance(self, monkeypatch):
        # Reset the module global so the test is order-independent.
        monkeypatch.setattr(proxy_manager, "_proxy_manager", None)
        a = get_proxy_manager()
        b = get_proxy_manager()
        assert a is b
        assert isinstance(a, AWSProxyManager)
