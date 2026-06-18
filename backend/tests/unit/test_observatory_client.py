"""Unit tests for observatory_client.py (the ObservatoryClient telemetry client).

`observatory_client.ObservatoryClient` is the SECOND SnowGlobe Observatory
reporting client on the backend (the module-level `snowglobe.py` is the first,
already covered). `register_with_observatory.py` and any code holding the
`get_observatory_client()` singleton report health, metrics, and events to the
Observatory dashboard through it. It had ZERO dedicated coverage, yet it is a
contract boundary in two directions a smoke test never exercises:

  - the emitted HTTP shape is a contract the Observatory consumes -- the endpoint
    path, the `x-api-key` header, and the `siteId`/`eventType`/`status` body
    fields. Renaming a field, dropping the site id, or moving the timestamp
    silently blinds the dashboard; and
  - the module is fail-open by design -- `_make_request` must SWALLOW a
    `requests.exceptions.Timeout` (logged at warning), any other
    `RequestException` (logged at warning), AND any other exception (logged at
    error), returning False, so a telemetry outage never raises into the request
    it is only meant to observe.

This client differs from `snowglobe.py` in several load-bearing ways that the
tests pin deliberately, so a future refactor that "unifies" the two cannot
silently change behavior:

  - it is an INSTANCE class configured from the environment in `__init__` (not
    module globals), and `enabled` is `bool(self.api_key)` -- an empty-string key
    is disabled;
  - `_make_request` returns a BOOL (True/False) via `response.raise_for_status()`,
    not the parsed JSON body, and its default timeout is 5s (snowglobe uses 10);
  - the `timestamp` is a TOP-LEVEL body field on every payload, and `track_event`
    nests the caller's `data` verbatim under a `data` key (it does NOT merge the
    data into the body or stamp a timestamp inside it, unlike snowglobe); and
  - `report_health` attaches `error` only when it is TRUTHY (`if error:`), so an
    empty-string error is dropped, while `responseTimeMs` uses `is not None` so a
    0ms reading IS sent.

Tests construct the client with explicit args to control the enabled state
without depending on the ambient environment, drive the env-default paths with
`monkeypatch.setenv`/`delenv`, and replace the only source of non-determinism --
`requests.post` -- with a recorder that captures the exact url/headers/json/timeout
the source built, so the request contract is asserted with no network.
"""
from datetime import datetime

import pytest
import requests

import observatory_client
from observatory_client import ObservatoryClient


class FakeResponse:
    """Stand-in for the requests.post() return value.

    `raise_for_status` records that it was called and optionally raises, to drive
    the success vs HTTP-error branches of `_make_request`.
    """

    def __init__(self, raise_exc: Exception | None = None):
        self._raise_exc = raise_exc
        self.raise_for_status_calls = 0

    def raise_for_status(self):
        self.raise_for_status_calls += 1
        if self._raise_exc is not None:
            raise self._raise_exc


class PostRecorder:
    """Recording replacement for requests.post.

    Captures every call's (url, headers, json, timeout) so the request contract
    can be asserted, returns `response`, or raises `exc` to drive the fail-open
    branches.
    """

    def __init__(self, response: FakeResponse | None = None, exc: Exception | None = None):
        self.calls = []
        self.response = response if response is not None else FakeResponse()
        self.exc = exc

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.calls.append(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        if self.exc is not None:
            raise self.exc
        return self.response


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level singleton so get_observatory_client tests don't
    leak a client built under a different env across tests."""
    observatory_client._observatory_client = None
    yield
    observatory_client._observatory_client = None


@pytest.fixture
def clear_env(monkeypatch):
    """Remove the SNOWGLOBE_* env so __init__ falls back to its literal defaults
    (conftest does not set them, but a real shell might)."""
    for var in ("SNOWGLOBE_URL", "SNOWGLOBE_API_KEY", "SNOWGLOBE_SITE_ID"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def post_rec(monkeypatch):
    """Replace requests.post (the reference the module resolves at call time via
    `requests.post`) with a recorder."""
    rec = PostRecorder()
    monkeypatch.setattr(observatory_client.requests, "post", rec)
    return rec


def _enabled_client():
    """A client wired to a known URL/key/site_id, independent of the env."""
    return ObservatoryClient(
        url="https://obs.test", api_key="key-abc", site_id="snowscrape"
    )


def _body(rec, index=0):
    return rec.calls[index]["json"]


# --------------------------------------------------------------------------- #
# __init__ / configuration
# --------------------------------------------------------------------------- #
class TestInit:
    def test_explicit_args_win_over_env(self, monkeypatch):
        monkeypatch.setenv("SNOWGLOBE_URL", "https://from-env")
        monkeypatch.setenv("SNOWGLOBE_API_KEY", "env-key")
        monkeypatch.setenv("SNOWGLOBE_SITE_ID", "env-site")

        c = ObservatoryClient(url="https://arg", api_key="arg-key", site_id="arg-site")

        assert c.url == "https://arg"
        assert c.api_key == "arg-key"
        assert c.site_id == "arg-site"

    def test_reads_from_env_when_no_args(self, monkeypatch):
        monkeypatch.setenv("SNOWGLOBE_URL", "https://from-env")
        monkeypatch.setenv("SNOWGLOBE_API_KEY", "env-key")
        monkeypatch.setenv("SNOWGLOBE_SITE_ID", "env-site")

        c = ObservatoryClient()

        assert c.url == "https://from-env"
        assert c.api_key == "env-key"
        assert c.site_id == "env-site"

    def test_url_falls_back_to_literal_default(self, clear_env):
        assert ObservatoryClient().url == "https://snowglobe.alexdiaz.me"

    def test_site_id_falls_back_to_snowscrape(self, clear_env):
        assert ObservatoryClient().site_id == "snowscrape"

    def test_api_key_default_is_none_and_disables_client(self, clear_env):
        c = ObservatoryClient()
        assert c.api_key is None
        assert c.enabled is False

    def test_enabled_is_true_only_with_a_key(self, clear_env):
        assert ObservatoryClient(api_key="x").enabled is True

    def test_empty_string_key_is_disabled(self, clear_env):
        """`enabled = bool(self.api_key)`, so an empty-string key is falsy =
        disabled (not just a None check)."""
        assert ObservatoryClient(api_key="").enabled is False


# --------------------------------------------------------------------------- #
# _make_request: the single HTTP chokepoint every helper funnels through
# --------------------------------------------------------------------------- #
class TestMakeRequest:
    def test_disabled_returns_false_without_network(self, clear_env, post_rec):
        c = ObservatoryClient(api_key=None)  # disabled

        result = c._make_request("/api/events", {"a": 1})

        assert result is False
        assert post_rec.calls == []

    def test_builds_url_from_base_plus_endpoint(self, post_rec):
        _enabled_client()._make_request("/api/events", {"a": 1})

        assert post_rec.calls[0]["url"] == "https://obs.test/api/events"

    def test_sends_api_key_and_content_type_headers(self, post_rec):
        _enabled_client()._make_request("/api/events", {"a": 1})

        headers = post_rec.calls[0]["headers"]
        assert headers["x-api-key"] == "key-abc"
        assert headers["Content-Type"] == "application/json"

    def test_forwards_payload_as_json_kwarg(self, post_rec):
        _enabled_client()._make_request("/api/events", {"a": 1, "b": "two"})

        assert post_rec.calls[0]["json"] == {"a": 1, "b": "two"}

    def test_default_timeout_is_five_seconds(self, post_rec):
        _enabled_client()._make_request("/api/events", {"a": 1})

        assert post_rec.calls[0]["timeout"] == 5

    def test_custom_timeout_is_forwarded(self, post_rec):
        _enabled_client()._make_request("/api/events", {"a": 1}, timeout=30)

        assert post_rec.calls[0]["timeout"] == 30

    def test_success_calls_raise_for_status_and_returns_true(self, monkeypatch):
        resp = FakeResponse()
        monkeypatch.setattr(observatory_client.requests, "post", PostRecorder(response=resp))

        result = _enabled_client()._make_request("/api/events", {"a": 1})

        assert result is True
        assert resp.raise_for_status_calls == 1  # the 2xx gate actually ran

    def test_timeout_fails_open_to_false(self, monkeypatch):
        """A requests Timeout is swallowed -> False, via the Timeout-specific
        except (warning, message 'timed out'), not the generic error branch."""
        rec = PostRecorder(exc=requests.exceptions.Timeout("slow"))
        monkeypatch.setattr(observatory_client.requests, "post", rec)
        warns, errors = [], []
        monkeypatch.setattr(observatory_client.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(observatory_client.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = _enabled_client()._make_request("/api/events", {"a": 1})

        assert result is False
        assert len(rec.calls) == 1  # it did attempt the request
        assert len(warns) == 1 and errors == []
        assert "timed out" in warns[0][0][0]  # the Timeout branch, not the RequestException one
        assert warns[0][1].get("endpoint") == "/api/events"  # structured-log shape preserved

    def test_request_exception_fails_open_to_false(self, monkeypatch):
        """A non-Timeout RequestException (e.g. ConnectionError) is swallowed ->
        False, via the RequestException branch (warning, message 'failed')."""
        rec = PostRecorder(exc=requests.exceptions.ConnectionError("refused"))
        monkeypatch.setattr(observatory_client.requests, "post", rec)
        warns, errors = [], []
        monkeypatch.setattr(observatory_client.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(observatory_client.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = _enabled_client()._make_request("/api/events", {"a": 1})

        assert result is False
        assert len(warns) == 1 and errors == []
        assert "failed" in warns[0][0][0]  # the RequestException branch, not Timeout
        assert warns[0][1].get("endpoint") == "/api/events"  # structured-log shape preserved

    def test_http_error_from_raise_for_status_fails_open(self, monkeypatch):
        """A non-2xx response raises HTTPError (a RequestException subclass) from
        raise_for_status, which the RequestException branch swallows -> False."""
        resp = FakeResponse(raise_exc=requests.exceptions.HTTPError("500"))
        monkeypatch.setattr(observatory_client.requests, "post", PostRecorder(response=resp))
        warns, errors = [], []
        monkeypatch.setattr(observatory_client.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(observatory_client.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = _enabled_client()._make_request("/api/events", {"a": 1})

        assert result is False
        assert len(warns) == 1 and errors == []  # HTTPError is a RequestException

    def test_generic_exception_fails_open_to_false(self, monkeypatch):
        """Any non-requests exception is caught by the broad except and logged at
        ERROR (distinguishes it from the warning branches)."""
        rec = PostRecorder(exc=ValueError("boom"))
        monkeypatch.setattr(observatory_client.requests, "post", rec)
        warns, errors = [], []
        monkeypatch.setattr(observatory_client.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(observatory_client.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = _enabled_client()._make_request("/api/events", {"a": 1})

        assert result is False
        assert len(errors) == 1 and warns == []  # broad except branch, not requests


# --------------------------------------------------------------------------- #
# report_health
# --------------------------------------------------------------------------- #
class TestReportHealth:
    def test_posts_to_site_health_endpoint(self, post_rec):
        _enabled_client().report_health("healthy")

        assert post_rec.calls[0]["url"] == "https://obs.test/api/sites/snowscrape/health"

    def test_body_carries_status_and_timestamp(self, post_rec):
        _enabled_client().report_health("degraded")

        body = _body(post_rec)
        assert body["status"] == "degraded"
        assert "timestamp" in body

    def test_timestamp_is_utc_iso(self, post_rec):
        _enabled_client().report_health("healthy")

        parsed = datetime.fromisoformat(_body(post_rec)["timestamp"])
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0

    def test_omits_details_when_none(self, post_rec):
        _enabled_client().report_health("healthy")

        assert set(_body(post_rec).keys()) == {"status", "timestamp"}

    def test_includes_response_time_only_when_provided(self, post_rec):
        _enabled_client().report_health("healthy", response_time_ms=123)

        body = _body(post_rec)
        assert body["responseTimeMs"] == 123
        assert "error" not in body

    def test_response_time_zero_is_included(self, post_rec):
        """The guard is `is not None`, so a 0ms reading is still attached."""
        _enabled_client().report_health("healthy", response_time_ms=0)

        assert _body(post_rec)["responseTimeMs"] == 0

    def test_includes_error_only_when_truthy(self, post_rec):
        _enabled_client().report_health("down", error="db unreachable")

        body = _body(post_rec)
        assert body["error"] == "db unreachable"
        assert "responseTimeMs" not in body

    def test_empty_string_error_is_dropped(self, post_rec):
        """`if error:` is a truthiness check (unlike snowglobe's `is not None`),
        so an empty-string error is NOT attached."""
        _enabled_client().report_health("healthy", error="")

        assert "error" not in _body(post_rec)

    def test_includes_both_details_when_both_provided(self, post_rec):
        _enabled_client().report_health("degraded", response_time_ms=900, error="slow")

        body = _body(post_rec)
        assert body["responseTimeMs"] == 900
        assert body["error"] == "slow"

    def test_returns_make_request_bool(self, monkeypatch):
        monkeypatch.setattr(observatory_client.requests, "post", PostRecorder())
        assert _enabled_client().report_health("healthy") is True

    def test_disabled_makes_no_request(self, clear_env, post_rec):
        ObservatoryClient(api_key=None).report_health("healthy")
        assert post_rec.calls == []


# --------------------------------------------------------------------------- #
# send_metrics
# --------------------------------------------------------------------------- #
class TestSendMetrics:
    def test_posts_to_metrics_endpoint(self, post_rec):
        _enabled_client().send_metrics({"cpu": 0.5})

        assert post_rec.calls[0]["url"] == "https://obs.test/api/metrics"

    def test_body_carries_site_id_metrics_and_timestamp(self, post_rec):
        _enabled_client().send_metrics({"cpu": 0.5, "mem": 128})

        body = _body(post_rec)
        assert body["siteId"] == "snowscrape"
        assert body["metrics"] == {"cpu": 0.5, "mem": 128}
        assert "timestamp" in body


# --------------------------------------------------------------------------- #
# track_event
# --------------------------------------------------------------------------- #
class TestTrackEvent:
    def test_posts_to_events_endpoint(self, post_rec):
        _enabled_client().track_event("deployment")

        assert post_rec.calls[0]["url"] == "https://obs.test/api/events"

    def test_body_carries_site_id_event_type_and_top_level_timestamp(self, post_rec):
        _enabled_client().track_event("deployment")

        body = _body(post_rec)
        assert body["siteId"] == "snowscrape"
        assert body["eventType"] == "deployment"
        # the timestamp lives at the TOP level, not inside `data` (unlike snowglobe)
        assert "timestamp" in body

    def test_nests_provided_data_verbatim_under_data_key(self, post_rec):
        _enabled_client().track_event("deployment", {"version": "1.2.0", "env": "prod"})

        body = _body(post_rec)
        assert body["data"] == {"version": "1.2.0", "env": "prod"}
        # data is NOT merged into the body and gets NO timestamp of its own
        assert "version" not in body
        assert "timestamp" not in body["data"]

    def test_omits_data_key_when_no_data(self, post_rec):
        _enabled_client().track_event("milestone")

        assert "data" not in _body(post_rec)

    def test_empty_dict_data_omits_data_key(self, post_rec):
        """`if data:` is a truthiness check, so an empty dict yields no `data`
        key at all."""
        _enabled_client().track_event("milestone", {})

        assert "data" not in _body(post_rec)


# --------------------------------------------------------------------------- #
# register
# --------------------------------------------------------------------------- #
class TestRegister:
    def test_posts_to_sites_endpoint(self, post_rec):
        _enabled_client().register("Snowscrape", "pipeline")

        assert post_rec.calls[0]["url"] == "https://obs.test/api/sites"

    def test_body_carries_identity_and_type(self, post_rec):
        _enabled_client().register("Snowscrape", "pipeline")

        body = _body(post_rec)
        assert body["siteId"] == "snowscrape"
        assert body["name"] == "Snowscrape"
        assert body["type"] == "pipeline"

    def test_kwargs_are_spread_into_body(self, post_rec):
        _enabled_client().register(
            "Snowscrape",
            "pipeline",
            platform="AWS Lambda",
            databases=["DynamoDB"],
        )

        body = _body(post_rec)
        assert body["platform"] == "AWS Lambda"
        assert body["databases"] == ["DynamoDB"]


# --------------------------------------------------------------------------- #
# send_batch_metrics (convenience wrapper over send_metrics)
# --------------------------------------------------------------------------- #
class TestSendBatchMetrics:
    def _call(self, client):
        return client.send_batch_metrics(
            jobs_processed=100,
            jobs_completed=95,
            jobs_failed=5,
            success_rate=95.0,
            avg_crawl_duration_ms=2500.0,
            active_jobs=3,
            queue_depth=7,
            urls_crawled=1234,
            error_rate=5.0,
        )

    def test_routes_through_send_metrics_to_metrics_endpoint(self, post_rec):
        self._call(_enabled_client())

        assert post_rec.calls[0]["url"] == "https://obs.test/api/metrics"

    def test_maps_every_field_to_its_camelcase_key(self, post_rec):
        self._call(_enabled_client())

        metrics = _body(post_rec)["metrics"]
        assert metrics == {
            "jobsProcessed": 100,
            "jobsCompleted": 95,
            "jobsFailed": 5,
            "successRate": 95.0,
            "avgCrawlDurationMs": 2500.0,
            "activeJobs": 3,
            "queueDepth": 7,
            "urlsCrawled": 1234,
            "errorRate": 5.0,
        }

    def test_rounds_the_float_fields_to_two_places(self, post_rec):
        _enabled_client().send_batch_metrics(
            jobs_processed=3,
            jobs_completed=2,
            jobs_failed=1,
            success_rate=66.66666,
            avg_crawl_duration_ms=1234.5678,
            active_jobs=1,
            queue_depth=0,
            urls_crawled=10,
            error_rate=33.33333,
        )

        metrics = _body(post_rec)["metrics"]
        assert metrics["successRate"] == 66.67
        assert metrics["avgCrawlDurationMs"] == 1234.57
        assert metrics["errorRate"] == 33.33


# --------------------------------------------------------------------------- #
# get_observatory_client singleton
# --------------------------------------------------------------------------- #
class TestGetObservatoryClient:
    def test_returns_an_observatory_client(self, clear_env):
        assert isinstance(observatory_client.get_observatory_client(), ObservatoryClient)

    def test_caches_a_single_instance(self, clear_env):
        first = observatory_client.get_observatory_client()
        second = observatory_client.get_observatory_client()
        assert first is second
