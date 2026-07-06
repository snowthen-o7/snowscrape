"""Unit tests for snowglobe.py (the SnowGlobe Observatory telemetry client).

snowglobe.py is the live-path analytics client: `handler.py` imports it and the
job path reports events, health, and metrics to the SnowGlobe Observatory over
HTTP. It had ZERO dedicated coverage, yet it is a contract boundary in two
directions a smoke test never exercises:

  - the emitted HTTP shape is a contract the Observatory consumes -- the endpoint
    path, the `x-api-key` header, the `siteId`/`eventType`/`status` body fields,
    and the per-helper payload keys (`job_completed` vs `job_failed`, the
    `responseTimeMs`/`error` health details). Renaming a field or dropping the
    site id silently blinds the dashboard; and
  - the module is fail-open by design -- `_make_request` must SWALLOW any
    `URLError` (logged at warning) AND any other exception (logged at error) and
    return None, so a telemetry outage never fails the request it is measuring. A
    regression turning either into a raising path would take down the live job
    path it is only supposed to observe.

There are also quiet load-bearing rules: the `SNOWGLOBE_ENABLED` gate
short-circuits to None (no network) when no API key is configured; `report_health`
attaches `responseTimeMs`/`error` ONLY when they are not None; and `track_event`
injects a UTC ISO timestamp into the event data.

KEY CONSTRAINT: `SNOWGLOBE_URL`/`SNOWGLOBE_API_KEY`/`SNOWGLOBE_SITE_ID`/
`SNOWGLOBE_ENABLED` are module-level globals computed from the environment at
IMPORT time, and `_make_request` reads them by module-global lookup at call time.
So tests configure the enabled state by monkeypatching those module attributes
(env changes after import would not take effect), and replace the only source of
non-determinism -- `urllib.request.urlopen` -- with a recording fake that captures
the `Request` object, so the exact URL / method / headers / body are asserted
without any network.
"""
import json
import urllib.error
import urllib.request
from datetime import datetime

import pytest

import snowglobe


class FakeResponse:
    """Context-manager stand-in for the urlopen() return value."""

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class UrlopenRecorder:
    """Recording replacement for urllib.request.urlopen.

    Captures every (Request, timeout) call so the request contract can be
    asserted, returns a FakeResponse with `body`, or raises `exc` to drive the
    fail-open branches.
    """

    def __init__(self, body: bytes = b'{"ok": true}', exc: Exception | None = None):
        self.calls = []  # list of (Request, timeout)
        self.body = body
        self.exc = exc

    def __call__(self, req, timeout=None):
        self.calls.append((req, timeout))
        if self.exc is not None:
            raise self.exc
        return FakeResponse(self.body)


def _headers_lower(req) -> dict:
    """urllib capitalizes header keys (x-api-key -> X-api-key); normalize them."""
    return {k.lower(): v for k, v in req.header_items()}


def _body_json(req):
    """Decode the JSON body the request was built with (None if no body)."""
    return json.loads(req.data.decode("utf-8")) if req.data else None


@pytest.fixture
def sg(monkeypatch):
    """Put snowglobe's module globals into a known ENABLED state.

    These are read at call time as module globals, so monkeypatching the module
    attributes is what actually flips the client on (it is configured from env
    only at import). monkeypatch restores the originals after the test.
    """
    monkeypatch.setattr(snowglobe, "SNOWGLOBE_URL", "https://glb.test")
    monkeypatch.setattr(snowglobe, "SNOWGLOBE_API_KEY", "test-key-123")
    monkeypatch.setattr(snowglobe, "SNOWGLOBE_SITE_ID", "snowscrape")
    monkeypatch.setattr(snowglobe, "SNOWGLOBE_ENABLED", True)
    return snowglobe


@pytest.fixture
def urlopen_rec(monkeypatch):
    """Replace urllib.request.urlopen with a recorder (the module calls it by
    `urllib.request.urlopen`, so patching the attribute on urllib.request is the
    reference it resolves at call time)."""
    rec = UrlopenRecorder()
    monkeypatch.setattr(urllib.request, "urlopen", rec)
    return rec


# --------------------------------------------------------------------------- #
# _make_request: the single HTTP chokepoint every helper funnels through
# --------------------------------------------------------------------------- #
class TestMakeRequest:
    def test_disabled_returns_none_without_network(self, monkeypatch, urlopen_rec):
        """With no API key the client is disabled: short-circuit to None and
        never touch the network."""
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_ENABLED", False)
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_API_KEY", "")

        result = snowglobe._make_request("/api/events", "POST", {"a": 1})

        assert result is None
        assert urlopen_rec.calls == []

    def test_builds_url_from_base_plus_endpoint(self, sg, urlopen_rec):
        snowglobe._make_request("/api/events", "POST", {"a": 1})

        req, _timeout = urlopen_rec.calls[0]
        assert req.get_full_url() == "https://glb.test/api/events"

    def test_sends_content_type_and_api_key_headers(self, sg, urlopen_rec):
        snowglobe._make_request("/api/events", "POST", {"a": 1})

        headers = _headers_lower(urlopen_rec.calls[0][0])
        assert headers["content-type"] == "application/json"
        assert headers["x-api-key"] == "test-key-123"

    def test_method_is_forwarded(self, sg, urlopen_rec):
        snowglobe._make_request("/api/sites/x/health", "PUT", {"status": "ok"})

        assert urlopen_rec.calls[0][0].get_method() == "PUT"

    def test_default_method_is_post(self, sg, urlopen_rec):
        snowglobe._make_request("/api/events", data={"a": 1})

        assert urlopen_rec.calls[0][0].get_method() == "POST"

    def test_encodes_dict_data_as_json_utf8(self, sg, urlopen_rec):
        snowglobe._make_request("/api/events", "POST", {"a": 1, "b": "two"})

        req = urlopen_rec.calls[0][0]
        assert isinstance(req.data, bytes)
        assert _body_json(req) == {"a": 1, "b": "two"}

    def test_none_data_sends_no_body(self, sg, urlopen_rec):
        """A None payload builds a Request with data=None (no body encoded)."""
        snowglobe._make_request("/api/ping", "GET", None)

        req = urlopen_rec.calls[0][0]
        assert req.data is None

    def test_timeout_is_ten_seconds(self, sg, urlopen_rec):
        snowglobe._make_request("/api/events", "POST", {"a": 1})

        assert urlopen_rec.calls[0][1] == 10

    def test_success_returns_parsed_json(self, sg, monkeypatch):
        monkeypatch.setattr(
            urllib.request, "urlopen", UrlopenRecorder(body=b'{"received": 5}')
        )

        result = snowglobe._make_request("/api/events", "POST", {"a": 1})

        assert result == {"received": 5}

    def test_urlerror_fails_open_to_none(self, sg, monkeypatch):
        """A URLError (network/DNS/connection) is swallowed and returns None,
        and is logged at WARNING (the URLError-specific except, not the broad
        one), so the test cannot pass via the wrong except clause."""
        rec = UrlopenRecorder(exc=urllib.error.URLError("connection refused"))
        monkeypatch.setattr(urllib.request, "urlopen", rec)
        warns, errors = [], []
        monkeypatch.setattr(snowglobe.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(snowglobe.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = snowglobe._make_request("/api/events", "POST", {"a": 1})

        assert result is None
        assert len(rec.calls) == 1  # it did attempt the request
        assert len(warns) == 1 and errors == []  # URLError branch, not generic

    def test_generic_exception_fails_open_to_none(self, sg, monkeypatch):
        """Any non-URLError exception is also swallowed by the broad except and
        logged at ERROR (distinguishes it from the URLError/warning branch)."""
        rec = UrlopenRecorder(exc=ValueError("boom"))
        monkeypatch.setattr(urllib.request, "urlopen", rec)
        warns, errors = [], []
        monkeypatch.setattr(snowglobe.logger, "warning", lambda *a, **k: warns.append((a, k)))
        monkeypatch.setattr(snowglobe.logger, "error", lambda *a, **k: errors.append((a, k)))

        result = snowglobe._make_request("/api/events", "POST", {"a": 1})

        assert result is None
        assert len(errors) == 1 and warns == []  # broad except branch, not URLError


# --------------------------------------------------------------------------- #
# track_event
# --------------------------------------------------------------------------- #
class TestTrackEvent:
    def test_posts_to_events_endpoint(self, sg, urlopen_rec):
        snowglobe.track_event("custom_event", {"k": "v"})

        req = urlopen_rec.calls[0][0]
        assert req.get_full_url() == "https://glb.test/api/events"
        assert req.get_method() == "POST"

    def test_body_carries_site_id_and_event_type(self, sg, urlopen_rec):
        snowglobe.track_event("custom_event", {"k": "v"})

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["siteId"] == "snowscrape"
        assert body["eventType"] == "custom_event"

    def test_preserves_provided_data_keys(self, sg, urlopen_rec):
        snowglobe.track_event("custom_event", {"k": "v", "n": 3})

        data = _body_json(urlopen_rec.calls[0][0])["data"]
        assert data["k"] == "v"
        assert data["n"] == 3

    def test_injects_utc_iso_timestamp(self, sg, urlopen_rec):
        snowglobe.track_event("custom_event", {"k": "v"})

        ts = _body_json(urlopen_rec.calls[0][0])["data"]["timestamp"]
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0

    def test_none_data_yields_data_with_only_timestamp(self, sg, urlopen_rec):
        snowglobe.track_event("custom_event")

        data = _body_json(urlopen_rec.calls[0][0])["data"]
        assert set(data.keys()) == {"timestamp"}

    def test_uses_configured_site_id(self, monkeypatch, urlopen_rec):
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_URL", "https://glb.test")
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_API_KEY", "test-key-123")
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_ENABLED", True)
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_SITE_ID", "other-site")

        snowglobe.track_event("custom_event")

        assert _body_json(urlopen_rec.calls[0][0])["siteId"] == "other-site"

    def test_disabled_makes_no_request_and_does_not_raise(self, monkeypatch, urlopen_rec):
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_ENABLED", False)

        snowglobe.track_event("custom_event", {"k": "v"})

        assert urlopen_rec.calls == []


# --------------------------------------------------------------------------- #
# report_health
# --------------------------------------------------------------------------- #
class TestReportHealth:
    def test_posts_to_site_health_endpoint(self, sg, urlopen_rec):
        snowglobe.report_health("healthy")

        req = urlopen_rec.calls[0][0]
        assert req.get_full_url() == "https://glb.test/api/sites/snowscrape/health"
        assert req.get_method() == "POST"

    def test_body_carries_status(self, sg, urlopen_rec):
        snowglobe.report_health("degraded")

        assert _body_json(urlopen_rec.calls[0][0])["status"] == "degraded"

    def test_omits_details_when_none(self, sg, urlopen_rec):
        """With no response time or error, the body is just the status."""
        snowglobe.report_health("healthy")

        assert _body_json(urlopen_rec.calls[0][0]) == {"status": "healthy"}

    def test_includes_response_time_only_when_provided(self, sg, urlopen_rec):
        snowglobe.report_health("healthy", response_time_ms=123)

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["responseTimeMs"] == 123
        assert "error" not in body

    def test_includes_error_only_when_provided(self, sg, urlopen_rec):
        snowglobe.report_health("down", error="timeout")

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["error"] == "timeout"
        assert "responseTimeMs" not in body

    def test_includes_both_details_when_both_provided(self, sg, urlopen_rec):
        snowglobe.report_health("degraded", response_time_ms=900, error="slow")

        body = _body_json(urlopen_rec.calls[0][0])
        assert body == {"status": "degraded", "responseTimeMs": 900, "error": "slow"}

    def test_response_time_zero_is_included(self, sg, urlopen_rec):
        """The guard is `is not None`, so a 0ms reading is still attached."""
        snowglobe.report_health("healthy", response_time_ms=0)

        assert _body_json(urlopen_rec.calls[0][0])["responseTimeMs"] == 0


# --------------------------------------------------------------------------- #
# send_metrics
# --------------------------------------------------------------------------- #
class TestSendMetrics:
    def test_posts_to_metrics_endpoint(self, sg, urlopen_rec):
        snowglobe.send_metrics({"cpu": 0.5})

        assert urlopen_rec.calls[0][0].get_full_url() == "https://glb.test/api/metrics"

    def test_body_carries_site_id_and_metrics(self, sg, urlopen_rec):
        snowglobe.send_metrics({"cpu": 0.5, "mem": 128})

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["siteId"] == "snowscrape"
        assert body["metrics"] == {"cpu": 0.5, "mem": 128}


# --------------------------------------------------------------------------- #
# register_site
# --------------------------------------------------------------------------- #
class TestRegisterSite:
    def test_posts_to_sites_endpoint(self, sg, urlopen_rec):
        snowglobe.register_site()

        assert urlopen_rec.calls[0][0].get_full_url() == "https://glb.test/api/sites"

    def test_body_carries_fixed_identity_fields(self, sg, urlopen_rec):
        snowglobe.register_site()

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["siteId"] == "snowscrape"
        assert body["name"] == "Snowscrape"
        assert body["type"] == "tool"
        assert body["platform"] == "AWS Lambda"
        assert body["repository"] == "snowthen-o7/snowscrape"
        assert body["databases"] == ["DynamoDB", "S3"]
        assert "AWS Lambda" in body["services"]


# --------------------------------------------------------------------------- #
# report_job_completed / report_job_failed (thin wrappers over track_event)
# --------------------------------------------------------------------------- #
class TestReportJob:
    def test_completed_emits_job_completed_event(self, sg, urlopen_rec):
        snowglobe.report_job_completed(
            "job-1", urls_processed=10, success_count=9, error_count=1, duration_ms=2500
        )

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["eventType"] == "job_completed"

    def test_completed_payload_carries_all_counts(self, sg, urlopen_rec):
        snowglobe.report_job_completed(
            "job-1", urls_processed=10, success_count=9, error_count=1, duration_ms=2500
        )

        data = _body_json(urlopen_rec.calls[0][0])["data"]
        assert data["job_id"] == "job-1"
        assert data["urls_processed"] == 10
        assert data["success_count"] == 9
        assert data["error_count"] == 1
        assert data["duration_ms"] == 2500
        assert "timestamp" in data  # routed through track_event

    def test_failed_emits_job_failed_event(self, sg, urlopen_rec):
        snowglobe.report_job_failed("job-2", "scrape error")

        body = _body_json(urlopen_rec.calls[0][0])
        assert body["eventType"] == "job_failed"

    def test_failed_payload_carries_job_id_and_error(self, sg, urlopen_rec):
        snowglobe.report_job_failed("job-2", "scrape error")

        data = _body_json(urlopen_rec.calls[0][0])["data"]
        assert data["job_id"] == "job-2"
        assert data["error"] == "scrape error"
        assert "timestamp" in data

    def test_report_helpers_no_network_when_disabled(self, monkeypatch, urlopen_rec):
        monkeypatch.setattr(snowglobe, "SNOWGLOBE_ENABLED", False)

        snowglobe.report_job_completed(
            "job-1", urls_processed=1, success_count=1, error_count=0, duration_ms=1
        )
        snowglobe.report_job_failed("job-2", "err")

        assert urlopen_rec.calls == []
