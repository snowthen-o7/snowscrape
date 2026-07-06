"""Unit tests for connection_pool.py (AWS client + HTTP session reuse layer).

connection_pool.py is a Lambda warm-start optimization: it caches boto3 clients,
DynamoDB tables, an in-memory job-session cache, env lookups, and per-job
`requests.Session` objects so warm invocations reuse connections instead of
rebuilding them. It had ZERO dedicated coverage, yet it is a reliability /
performance boundary with several non-obvious load-bearing contracts that a
silent regression would quietly break:

  - the module-global singleton short-circuit (`if _x is None`) is what makes a
    warm Lambda reuse a connection; a regression that rebuilt the client on every
    call would defeat the whole module and is invisible to a smoke test;
  - the boto3 `Config` each client is built with (`max_pool_connections=50`,
    adaptive `max_attempts=3` retries, and S3 path-style addressing) is the
    pool/retry contract under load;
  - the session-data cache's TTL semantics (strict `<` boundary, purge-on-expiry,
    a falsy-but-present value is a real hit, an entry missing its TTL row is
    treated as expired) are correctness contracts;
  - `get_env_cached` is an `lru_cache`, so the FIRST (key, default) call wins and
    later env changes for the same args return the STALE value, and the `default`
    is part of the cache key;
  - the HTTP session pool reuses by job_id, mounts a retry adapter with specific
    pool sizes, and CAPS the cache at 100 entries (past the cap a session is
    returned but NOT cached, so the next call builds a fresh one);
  - `warm_up_connections` must SWALLOW any error (a cold-start warmup failure must
    never break the handler).

The module's only non-determinism is `boto3.client`/`boto3.resource`, the wall
clock (`time.time`), and `os.environ`. boto3 is patched with a recorder so the
construction kwargs (region + Config) are asserted without AWS; `time.time` is
driven by a FakeClock; the session/HTTP caches are reset between tests. The 4
AWS-client module globals are already reset by conftest's autouse
`reset_connection_pool` fixture.
"""
import time

import pytest

import connection_pool


@pytest.fixture(autouse=True)
def reset_pool_state():
    """Reset the caches conftest's fixture does not cover, between tests.

    conftest resets the 4 boto3-client globals; here we also clear the
    session-data cache, its TTL map, the HTTP session pool, and the
    `get_env_cached` lru_cache so no value leaks across tests and masks a
    no-entry/no-cache path.
    """
    connection_pool._session_cache.clear()
    connection_pool._cache_ttl.clear()
    connection_pool._http_session_pool.clear()
    connection_pool.get_env_cached.cache_clear()
    yield
    connection_pool._session_cache.clear()
    connection_pool._cache_ttl.clear()
    connection_pool._http_session_pool.clear()
    connection_pool.get_env_cached.cache_clear()


@pytest.fixture
def boto_recorder(monkeypatch):
    """Patch boto3.client/resource with recorders that capture construction args.

    Each call returns a distinct sentinel (so a cached vs freshly-built client is
    distinguishable) and records the service name + kwargs (region_name, config).
    The real `boto3.session.Config(...)` still runs, so the returned Config object
    carries the genuine max_pool_connections / retries / s3 attributes to assert.
    """
    # `order` is a single combined log so call ORDER across client+resource is
    # observable (not just the per-type relative order).
    calls = {"client": [], "resource": [], "order": []}

    def fake_client(service, **kwargs):
        obj = ("client", service, len(calls["client"]))
        calls["client"].append({"service": service, "kwargs": kwargs, "obj": obj})
        calls["order"].append(service)
        return obj

    def fake_resource(service, **kwargs):
        obj = ("resource", service, len(calls["resource"]))
        calls["resource"].append({"service": service, "kwargs": kwargs, "obj": obj})
        calls["order"].append(service)
        return obj

    monkeypatch.setattr(connection_pool.boto3, "client", fake_client)
    monkeypatch.setattr(connection_pool.boto3, "resource", fake_resource)
    return calls


class FakeClock:
    """Controllable stand-in for time.time()."""

    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class FakeSession:
    """Minimal requests.Session stand-in that records close()."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


# --------------------------------------------------------------------------- #
# AWS client singletons
# --------------------------------------------------------------------------- #
class TestAwsClientSingletons:
    def test_dynamodb_resource_built_once_and_reused(self, boto_recorder):
        first = connection_pool.get_dynamodb_resource()
        second = connection_pool.get_dynamodb_resource()
        assert first is second
        assert len(boto_recorder["resource"]) == 1  # warm-start reuse, not rebuilt

    def test_dynamodb_resource_uses_region_env(self, monkeypatch, boto_recorder):
        monkeypatch.setenv("REGION", "eu-west-1")
        connection_pool.get_dynamodb_resource()
        assert boto_recorder["resource"][0]["kwargs"]["region_name"] == "eu-west-1"

    def test_dynamodb_resource_defaults_region_us_east_2(self, monkeypatch, boto_recorder):
        monkeypatch.delenv("REGION", raising=False)
        connection_pool.get_dynamodb_resource()
        assert boto_recorder["resource"][0]["kwargs"]["region_name"] == "us-east-2"
        assert boto_recorder["resource"][0]["service"] == "dynamodb"

    def test_dynamodb_resource_config_pool_and_retries(self, boto_recorder):
        connection_pool.get_dynamodb_resource()
        cfg = boto_recorder["resource"][0]["kwargs"]["config"]
        assert cfg.max_pool_connections == 50
        assert cfg.retries == {"max_attempts": 3, "mode": "adaptive"}

    def test_dynamodb_client_built_once_and_reused(self, boto_recorder):
        first = connection_pool.get_dynamodb_client()
        second = connection_pool.get_dynamodb_client()
        assert first is second
        assert len(boto_recorder["client"]) == 1
        assert boto_recorder["client"][0]["service"] == "dynamodb"

    def test_dynamodb_client_region_and_config(self, monkeypatch, boto_recorder):
        monkeypatch.setenv("REGION", "us-west-2")
        connection_pool.get_dynamodb_client()
        kwargs = boto_recorder["client"][0]["kwargs"]
        assert kwargs["region_name"] == "us-west-2"
        assert kwargs["config"].max_pool_connections == 50
        assert kwargs["config"].retries == {"max_attempts": 3, "mode": "adaptive"}

    def test_resource_and_client_are_independent_singletons(self, boto_recorder):
        res = connection_pool.get_dynamodb_resource()
        cli = connection_pool.get_dynamodb_client()
        # Different globals: building one must not satisfy the other.
        assert res != cli
        assert len(boto_recorder["resource"]) == 1
        assert len(boto_recorder["client"]) == 1

    def test_s3_client_built_once_and_reused(self, boto_recorder):
        first = connection_pool.get_s3_client()
        second = connection_pool.get_s3_client()
        assert first is second
        assert len(boto_recorder["client"]) == 1
        assert boto_recorder["client"][0]["service"] == "s3"

    def test_s3_client_uses_path_addressing_and_no_region(self, boto_recorder):
        connection_pool.get_s3_client()
        kwargs = boto_recorder["client"][0]["kwargs"]
        cfg = kwargs["config"]
        # S3-specific: path-style addressing; pool + retries match the others.
        assert cfg.s3 == {"addressing_style": "path"}
        assert cfg.max_pool_connections == 50
        assert cfg.retries == {"max_attempts": 3, "mode": "adaptive"}
        # The S3 client is deliberately built WITHOUT region_name (unlike the rest).
        assert "region_name" not in kwargs

    def test_sqs_client_built_once_and_reused(self, boto_recorder):
        first = connection_pool.get_sqs_client()
        second = connection_pool.get_sqs_client()
        assert first is second
        assert len(boto_recorder["client"]) == 1
        assert boto_recorder["client"][0]["service"] == "sqs"

    def test_sqs_client_region_and_config(self, monkeypatch, boto_recorder):
        monkeypatch.setenv("REGION", "ap-south-1")
        connection_pool.get_sqs_client()
        kwargs = boto_recorder["client"][0]["kwargs"]
        assert kwargs["region_name"] == "ap-south-1"
        assert kwargs["config"].max_pool_connections == 50
        assert kwargs["config"].retries == {"max_attempts": 3, "mode": "adaptive"}

    def test_get_table_delegates_to_resource(self, monkeypatch):
        class FakeResource:
            def __init__(self):
                self.table_calls = []

            def Table(self, name):
                self.table_calls.append(name)
                return ("table", name)

        fake_res = FakeResource()
        monkeypatch.setattr(connection_pool, "get_dynamodb_resource", lambda: fake_res)
        result = connection_pool.get_table("SnowscrapeJobs")
        assert result == ("table", "SnowscrapeJobs")
        assert fake_res.table_calls == ["SnowscrapeJobs"]


# --------------------------------------------------------------------------- #
# In-memory session-data cache
# --------------------------------------------------------------------------- #
class TestSessionDataCache:
    def test_get_unknown_job_returns_none(self):
        assert connection_pool.get_cached_session_data("nope") is None

    def test_set_then_get_roundtrip(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        data = {"cookies": "abc"}
        connection_pool.set_cached_session_data("j1", data)
        assert connection_pool.get_cached_session_data("j1") == data

    def test_set_uses_default_ttl_3600(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {"x": 1})
        assert connection_pool._cache_ttl["j1"] == 1000.0 + 3600

    def test_set_honors_custom_ttl(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {"x": 1}, ttl_seconds=10)
        assert connection_pool._cache_ttl["j1"] == 1010.0

    def test_not_yet_expired_returns_value(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {"x": 1}, ttl_seconds=100)
        clock.t = 1099.0  # still inside the window
        assert connection_pool.get_cached_session_data("j1") == {"x": 1}

    def test_expired_entry_returns_none_and_purges(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {"x": 1}, ttl_seconds=100)
        clock.t = 2000.0  # well past expiry
        assert connection_pool.get_cached_session_data("j1") is None
        # purged from BOTH maps so it cannot resurrect
        assert "j1" not in connection_pool._session_cache
        assert "j1" not in connection_pool._cache_ttl

    def test_expiry_boundary_is_strict_less_than(self, monkeypatch):
        # Source uses `time.time() < ttl`, so equality counts as EXPIRED.
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {"x": 1}, ttl_seconds=100)
        clock.t = 1100.0  # exactly the expiry instant
        assert connection_pool.get_cached_session_data("j1") is None

    def test_entry_without_ttl_row_treated_as_expired(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        # Present in the value cache but with no TTL row -> else branch -> purge.
        connection_pool._session_cache["orphan"] = {"x": 1}
        assert connection_pool.get_cached_session_data("orphan") is None
        assert "orphan" not in connection_pool._session_cache

    def test_falsy_but_present_value_is_a_real_hit(self, monkeypatch):
        # An empty dict is returned verbatim, not swallowed as a miss.
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("j1", {})
        result = connection_pool.get_cached_session_data("j1")
        assert result == {}
        assert result is connection_pool._session_cache["j1"]

    def test_clear_single_job(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("a", {"x": 1})
        connection_pool.set_cached_session_data("b", {"y": 2})
        connection_pool.clear_session_cache("a")
        assert "a" not in connection_pool._session_cache
        assert "a" not in connection_pool._cache_ttl
        assert connection_pool.get_cached_session_data("b") == {"y": 2}

    def test_clear_all_jobs(self, monkeypatch):
        clock = FakeClock(1000.0)
        monkeypatch.setattr(time, "time", clock)
        connection_pool.set_cached_session_data("a", {"x": 1})
        connection_pool.set_cached_session_data("b", {"y": 2})
        connection_pool.clear_session_cache()
        assert connection_pool._session_cache == {}
        assert connection_pool._cache_ttl == {}

    def test_clear_unknown_job_is_noop(self):
        connection_pool.clear_session_cache("ghost")  # must not raise


# --------------------------------------------------------------------------- #
# get_env_cached (lru_cache) -- staleness + default-as-key are the contracts
# --------------------------------------------------------------------------- #
class TestGetEnvCached:
    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("SNOW_TEST_KEY", "present")
        assert connection_pool.get_env_cached("SNOW_TEST_KEY") == "present"

    def test_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("SNOW_MISSING", raising=False)
        assert connection_pool.get_env_cached("SNOW_MISSING", "fallback") == "fallback"

    def test_caches_first_value_and_returns_stale_after_change(self, monkeypatch):
        monkeypatch.setenv("SNOW_TEST_KEY", "first")
        assert connection_pool.get_env_cached("SNOW_TEST_KEY") == "first"
        monkeypatch.setenv("SNOW_TEST_KEY", "second")
        # lru_cache: same args -> the FIRST result is returned, env change ignored.
        assert connection_pool.get_env_cached("SNOW_TEST_KEY") == "first"

    def test_default_is_part_of_the_cache_key(self, monkeypatch):
        monkeypatch.delenv("SNOW_MISSING", raising=False)
        assert connection_pool.get_env_cached("SNOW_MISSING") is None
        # Different default -> distinct cache entry, so this is NOT the cached None.
        assert connection_pool.get_env_cached("SNOW_MISSING", "x") == "x"

    def test_cache_clear_picks_up_new_env(self, monkeypatch):
        monkeypatch.setenv("SNOW_TEST_KEY", "first")
        assert connection_pool.get_env_cached("SNOW_TEST_KEY") == "first"
        connection_pool.get_env_cached.cache_clear()
        monkeypatch.setenv("SNOW_TEST_KEY", "second")
        assert connection_pool.get_env_cached("SNOW_TEST_KEY") == "second"


# --------------------------------------------------------------------------- #
# warm_up_connections -- must call the getters and never raise
# --------------------------------------------------------------------------- #
class TestWarmUpConnections:
    def test_warms_resource_s3_and_sqs_in_order(self, boto_recorder):
        connection_pool.warm_up_connections()
        # Observed call ORDER (single combined log): resource dynamodb, then s3, then sqs.
        assert boto_recorder["order"] == ["dynamodb", "s3", "sqs"]

    def test_swallows_errors(self, monkeypatch):
        def boom():
            raise RuntimeError("cold-start failure")

        reached = []
        monkeypatch.setattr(connection_pool, "get_dynamodb_resource", boom)
        monkeypatch.setattr(connection_pool, "get_s3_client", lambda: reached.append("s3"))
        monkeypatch.setattr(connection_pool, "get_sqs_client", lambda: reached.append("sqs"))
        # Must not propagate: a warmup failure cannot break the handler. And since
        # all three getters share one try, the first raising skips the rest.
        assert connection_pool.warm_up_connections() is None
        assert reached == []


# --------------------------------------------------------------------------- #
# HTTP session pool
# --------------------------------------------------------------------------- #
class TestHttpSessionPool:
    def test_returns_a_requests_session(self):
        import requests

        session = connection_pool.get_http_session("job-1")
        assert isinstance(session, requests.Session)

    def test_same_job_reuses_session(self):
        first = connection_pool.get_http_session("job-1")
        second = connection_pool.get_http_session("job-1")
        assert first is second

    def test_user_agent_header_set(self):
        session = connection_pool.get_http_session("job-1", user_agent="SnowBot/1.0")
        assert session.headers["User-Agent"] == "SnowBot/1.0"

    def test_referrer_set_as_referer_header(self):
        session = connection_pool.get_http_session("job-1", referrer="https://ref.example")
        assert session.headers["Referer"] == "https://ref.example"

    def test_no_ua_or_referrer_leaves_referer_absent(self):
        session = connection_pool.get_http_session("job-1")
        assert "Referer" not in session.headers

    def test_retry_strategy_contract(self):
        session = connection_pool.get_http_session("job-1")
        retry = session.get_adapter("https://example.com").max_retries
        assert retry.total == 3
        assert retry.backoff_factor == 1
        assert set(retry.status_forcelist) == {429, 500, 502, 503, 504}
        assert set(retry.allowed_methods) == {"HEAD", "GET", "OPTIONS"}

    def test_adapter_pool_sizes(self):
        session = connection_pool.get_http_session("job-1")
        adapter = session.get_adapter("https://example.com")
        assert adapter._pool_connections == 10
        assert adapter._pool_maxsize == 20
        assert adapter._pool_block is False

    def test_pool_caps_at_100_and_stops_caching(self):
        # Fill the cache to its 100-entry limit.
        for i in range(100):
            connection_pool.get_http_session(f"job-{i}")
        assert len(connection_pool._http_session_pool) == 100
        # The 101st distinct job is served but NOT cached (len < 100 is False)...
        over_first = connection_pool.get_http_session("job-over")
        assert "job-over" not in connection_pool._http_session_pool
        # ...so a second call for it builds a DIFFERENT session.
        over_second = connection_pool.get_http_session("job-over")
        assert over_first is not over_second

    def test_close_http_session_closes_and_removes(self):
        fake = FakeSession()
        connection_pool._http_session_pool["job-1"] = fake
        connection_pool.close_http_session("job-1")
        assert fake.closed is True
        assert "job-1" not in connection_pool._http_session_pool

    def test_close_unknown_session_is_noop(self):
        connection_pool.close_http_session("ghost")  # must not raise

    def test_cleanup_closes_all_and_clears_pool(self):
        a, b = FakeSession(), FakeSession()
        connection_pool._http_session_pool["a"] = a
        connection_pool._http_session_pool["b"] = b
        connection_pool.cleanup_http_sessions()
        assert a.closed is True
        assert b.closed is True
        assert connection_pool._http_session_pool == {}
