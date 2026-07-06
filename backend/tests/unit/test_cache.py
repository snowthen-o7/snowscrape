"""Unit tests for cache.py (the Redis caching layer).

cache.py is a fail-open caching wrapper over Upstash (serverless, in the Lambda)
or a standard Redis (local dev). It had ZERO dedicated coverage, yet its defining
contract is a RELIABILITY boundary: every operation must degrade gracefully when
Redis is missing or erroring. If a regression turned any of these into a raising
path, a transient Redis outage would take down the live scrape/data path that
caches behind it instead of silently running uncached. So these tests pin, for
every function, that:
  - a missing client (no REDIS_URL / failed connect) returns the documented
    "no-op" value (None for reads, False for writes) and never raises, and
  - a client that itself raises is swallowed and reported as the same no-op.

The module's only non-determinism is `os.environ['REDIS_URL']`, the lazily
`import`ed `redis` package, and the cached `_redis_client` singleton. The
read/write helpers all funnel through `get_redis_client()`, so most tests patch
that boundary directly (`cache.get_redis_client`) to hand the function a fake
client or None; the `get_redis_client` tests instead drive the real singleton
logic by injecting a fake `redis` module into `sys.modules` (the source does a
function-local `import redis`, so this is the reference it resolves at call time)
and controlling `REDIS_URL`.
"""
import json
import sys

import pytest

import cache


@pytest.fixture(autouse=True)
def reset_cache_singleton(monkeypatch):
    """Reset the module-level Redis client + REDIS_URL between tests.

    `get_redis_client` caches its client in the module global `_redis_client`,
    so a value leaking across tests would mask the no-client paths. Start every
    test with no cached client and no REDIS_URL unless the test sets one.
    """
    monkeypatch.setattr(cache, "_redis_client", None)
    monkeypatch.delenv("REDIS_URL", raising=False)
    yield
    cache._redis_client = None


class FakeRedis:
    """Controllable stand-in for a redis client.

    Each method either returns a queued/stored value or, when its `*_error`
    attribute is set, raises, so a test can exercise both the happy path and the
    fail-open path of every wrapper.
    """

    def __init__(self):
        self.store: dict = {}
        self.setex_calls: list = []
        self.delete_calls: list = []
        self.scan_pages: list = []          # list of (next_cursor, keys) to return in order
        self.scan_calls: list = []
        self.get_error: Exception | None = None
        self.setex_error: Exception | None = None
        self.delete_error: Exception | None = None
        self.scan_error: Exception | None = None

    def ping(self):
        return True

    def get(self, key):
        if self.get_error:
            raise self.get_error
        return self.store.get(key)

    def setex(self, key, ttl, value):
        if self.setex_error:
            raise self.setex_error
        self.setex_calls.append((key, ttl, value))
        self.store[key] = value

    def delete(self, *keys):
        if self.delete_error:
            raise self.delete_error
        self.delete_calls.append(keys)
        for k in keys:
            self.store.pop(k, None)

    def scan(self, cursor, match=None, count=None):
        if self.scan_error:
            raise self.scan_error
        self.scan_calls.append((cursor, match, count))
        return self.scan_pages.pop(0)


@pytest.fixture
def fake_client(monkeypatch):
    """A FakeRedis wired in as the resolved client for the read/write helpers."""
    client = FakeRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)
    return client


@pytest.fixture
def no_client(monkeypatch):
    """Force get_redis_client to report Redis unavailable."""
    monkeypatch.setattr(cache, "get_redis_client", lambda: None)


# --------------------------------------------------------------------------- #
# get_redis_client (singleton + connection + fail-open)
# --------------------------------------------------------------------------- #
class FakeRedisModule:
    """A fake `redis` module exposing `from_url`, injected into sys.modules."""

    def __init__(self, client=None, from_url_error=None):
        self._client = client if client is not None else FakeRedis()
        self._from_url_error = from_url_error
        self.from_url_calls: list = []

    def from_url(self, url, **kwargs):
        self.from_url_calls.append((url, kwargs))
        if self._from_url_error:
            raise self._from_url_error
        return self._client


class TestGetRedisClient:
    def test_no_redis_url_returns_none_and_does_not_cache(self, monkeypatch):
        # No REDIS_URL: short-circuit before any import, return None, cache nothing.
        sentinel_module = FakeRedisModule()
        monkeypatch.setitem(sys.modules, "redis", sentinel_module)
        assert cache.get_redis_client() is None
        assert cache._redis_client is None
        assert sentinel_module.from_url_calls == []  # never tried to connect

    def test_successful_connect_returns_and_caches_client(self, monkeypatch):
        client = FakeRedis()
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(sys.modules, "redis", FakeRedisModule(client=client))
        result = cache.get_redis_client()
        assert result is client
        assert cache._redis_client is client  # cached for reuse

    def test_connect_passes_the_lambda_safe_socket_options(self, monkeypatch):
        # These kwargs are a reliability contract: the short socket timeouts are
        # what stop a dead Redis from hanging the Lambda, and decode_responses=True
        # is why cache_get can json.loads a str rather than bytes.
        module = FakeRedisModule()
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(sys.modules, "redis", module)
        cache.get_redis_client()
        url, kwargs = module.from_url_calls[0]
        assert url == "redis://example:6379"
        assert kwargs == {
            "decode_responses": True,
            "socket_timeout": 2,
            "socket_connect_timeout": 2,
            "retry_on_timeout": True,
        }

    def test_ping_is_called_to_verify_the_connection(self, monkeypatch):
        client = FakeRedis()
        pinged = []
        client.ping = lambda: pinged.append(True)
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(sys.modules, "redis", FakeRedisModule(client=client))
        cache.get_redis_client()
        assert pinged == [True]

    def test_singleton_short_circuits_before_reading_env_or_connecting(self, monkeypatch):
        # An already-cached client is returned without re-importing/reconnecting,
        # even with no REDIS_URL set.
        existing = FakeRedis()
        monkeypatch.setattr(cache, "_redis_client", existing)
        module = FakeRedisModule()
        monkeypatch.setitem(sys.modules, "redis", module)
        assert cache.get_redis_client() is existing
        assert module.from_url_calls == []

    def test_from_url_failure_is_fail_open(self, monkeypatch):
        # A connection error must yield None and leave the singleton unset (so a
        # later call can retry), not propagate.
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(
            sys.modules, "redis",
            FakeRedisModule(from_url_error=ConnectionError("refused")),
        )
        assert cache.get_redis_client() is None
        assert cache._redis_client is None

    def test_ping_failure_is_fail_open(self, monkeypatch):
        client = FakeRedis()
        def boom():
            raise TimeoutError("ping timed out")
        client.ping = boom
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(sys.modules, "redis", FakeRedisModule(client=client))
        assert cache.get_redis_client() is None
        assert cache._redis_client is None

    def test_missing_redis_package_is_fail_open(self, monkeypatch):
        # sys.modules['redis'] = None makes `import redis` raise ImportError,
        # which the broad except must swallow into a None (uncached) result.
        monkeypatch.setenv("REDIS_URL", "redis://example:6379")
        monkeypatch.setitem(sys.modules, "redis", None)
        assert cache.get_redis_client() is None
        assert cache._redis_client is None


# --------------------------------------------------------------------------- #
# cache_get
# --------------------------------------------------------------------------- #
class TestCacheGet:
    def test_no_client_returns_none(self, no_client):
        assert cache.cache_get("k") is None

    def test_hit_deserializes_json_and_prefixes_the_key(self, fake_client):
        fake_client.store["snowscrape:user:1"] = json.dumps({"a": 1, "b": [2, 3]})
        assert cache.cache_get("user:1") == {"a": 1, "b": [2, 3]}

    def test_miss_returns_none(self, fake_client):
        # key absent -> client.get returns None -> cache_get returns None
        assert cache.cache_get("absent") is None

    def test_falsy_but_present_value_is_returned_not_treated_as_miss(self, fake_client):
        # A cached 0 / "" / [] is a real hit (json "0" is not None), so it must
        # round-trip rather than be swallowed by the None-miss check.
        fake_client.store["snowscrape:zero"] = json.dumps(0)
        assert cache.cache_get("zero") == 0

    def test_client_error_is_fail_open(self, fake_client):
        fake_client.get_error = RuntimeError("connection reset")
        assert cache.cache_get("k") is None

    def test_invalid_json_is_fail_open(self, fake_client):
        # A corrupt cached value must not crash the caller.
        fake_client.store["snowscrape:bad"] = "{not valid json"
        assert cache.cache_get("bad") is None


# --------------------------------------------------------------------------- #
# cache_set
# --------------------------------------------------------------------------- #
class TestCacheSet:
    def test_no_client_returns_false(self, no_client):
        assert cache.cache_set("k", {"v": 1}) is False

    def test_success_uses_setex_with_prefix_default_ttl_and_json(self, fake_client):
        assert cache.cache_set("user:1", {"v": 1}) is True
        key, ttl, value = fake_client.setex_calls[0]
        assert key == "snowscrape:user:1"
        assert ttl == 60  # documented default
        assert json.loads(value) == {"v": 1}

    def test_custom_ttl_is_forwarded(self, fake_client):
        cache.cache_set("k", "v", ttl=3600)
        _, ttl, _ = fake_client.setex_calls[0]
        assert ttl == 3600

    def test_non_json_native_value_serialized_via_default_str(self, fake_client):
        # json.dumps(..., default=str) lets non-JSON-native values (e.g. datetime)
        # be cached as their str() rather than raising TypeError.
        from datetime import datetime
        when = datetime(2026, 6, 16, 12, 0, 0)
        assert cache.cache_set("ts", when) is True
        _, _, value = fake_client.setex_calls[0]
        assert json.loads(value) == str(when)

    def test_client_error_is_fail_open(self, fake_client):
        fake_client.setex_error = RuntimeError("write failed")
        assert cache.cache_set("k", "v") is False


# --------------------------------------------------------------------------- #
# cache_delete
# --------------------------------------------------------------------------- #
class TestCacheDelete:
    def test_no_client_returns_false(self, no_client):
        assert cache.cache_delete("k") is False

    def test_success_deletes_prefixed_key(self, fake_client):
        assert cache.cache_delete("user:1") is True
        assert fake_client.delete_calls == [("snowscrape:user:1",)]

    def test_client_error_is_fail_open(self, fake_client):
        fake_client.delete_error = RuntimeError("delete failed")
        assert cache.cache_delete("k") is False


# --------------------------------------------------------------------------- #
# cache_delete_pattern
# --------------------------------------------------------------------------- #
class TestCacheDeletePattern:
    def test_no_client_returns_false(self, no_client):
        assert cache.cache_delete_pattern("user:*") is False

    def test_single_page_deletes_matched_keys_and_uses_prefixed_match(self, fake_client):
        fake_client.scan_pages = [(0, ["snowscrape:user:1", "snowscrape:user:2"])]
        assert cache.cache_delete_pattern("user:*") is True
        # match arg carries the prefix and the scan page size is 100
        cursor, match, count = fake_client.scan_calls[0]
        assert cursor == 0
        assert match == "snowscrape:user:*"
        assert count == 100
        assert fake_client.delete_calls == [("snowscrape:user:1", "snowscrape:user:2")]

    def test_paginates_until_cursor_zero(self, fake_client):
        # Two pages: cursor 5 -> then 0. Both batches deleted, scan called twice,
        # the second scan resumes from the cursor the first returned.
        fake_client.scan_pages = [(5, ["snowscrape:a"]), (0, ["snowscrape:b"])]
        assert cache.cache_delete_pattern("*") is True
        assert [c[0] for c in fake_client.scan_calls] == [0, 5]
        assert fake_client.delete_calls == [("snowscrape:a",), ("snowscrape:b",)]

    def test_empty_match_set_does_not_call_delete(self, fake_client):
        # No keys matched -> no delete issued, but still a success.
        fake_client.scan_pages = [(0, [])]
        assert cache.cache_delete_pattern("none:*") is True
        assert fake_client.delete_calls == []

    def test_client_error_is_fail_open(self, fake_client):
        fake_client.scan_error = RuntimeError("scan failed")
        assert cache.cache_delete_pattern("*") is False


# --------------------------------------------------------------------------- #
# cache_get_or_set
# --------------------------------------------------------------------------- #
class TestCacheGetOrSet:
    def test_hit_returns_cached_and_skips_factory_and_set(self, monkeypatch):
        calls = {"factory": 0, "set": []}

        def factory():
            calls["factory"] += 1
            return "fresh"

        monkeypatch.setattr(cache, "cache_get", lambda key: "cached")
        monkeypatch.setattr(
            cache, "cache_set",
            lambda key, value, ttl=60: calls["set"].append((key, value, ttl)),
        )
        assert cache.cache_get_or_set("k", factory) == "cached"
        assert calls["factory"] == 0      # factory not invoked on a hit
        assert calls["set"] == []         # nothing re-cached on a hit

    def test_miss_calls_factory_then_caches_and_returns_value(self, monkeypatch):
        calls = {"factory": 0, "set": []}

        def factory():
            calls["factory"] += 1
            return "computed"

        monkeypatch.setattr(cache, "cache_get", lambda key: None)
        monkeypatch.setattr(
            cache, "cache_set",
            lambda key, value, ttl=60: calls["set"].append((key, value, ttl)),
        )
        assert cache.cache_get_or_set("k", factory, ttl=120) == "computed"
        assert calls["factory"] == 1
        assert calls["set"] == [("k", "computed", 120)]

    def test_falsy_cached_value_counts_as_a_hit(self, monkeypatch):
        # cache_get_or_set checks `cached is not None`, so a cached 0/""/[] is a
        # hit and the factory must NOT run (the distinguishing characterization).
        calls = {"factory": 0}

        def factory():
            calls["factory"] += 1
            return "should-not-run"

        monkeypatch.setattr(cache, "cache_get", lambda key: 0)
        monkeypatch.setattr(cache, "cache_set", lambda key, value, ttl=60: None)
        assert cache.cache_get_or_set("k", factory) == 0
        assert calls["factory"] == 0
