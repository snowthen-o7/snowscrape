"""Unit tests for metrics.py (CloudWatch custom business-KPI metrics).

metrics.py is the operational-telemetry layer the live job path emits through
(`handler.py` and `job_manager.py` both call `get_metrics_emitter()`): every
crawl, query, S3 upload, and job lifecycle transition puts a custom CloudWatch
metric. It had ZERO dedicated coverage, yet it is a contract boundary in two
directions that a smoke test never exercises:

  - the emitted metric NAME / UNIT / DIMENSIONS are consumed by CloudWatch
    dashboards and alarms, so renaming `CrawlSuccess`, dropping the `JobId`
    dimension, sending `Count` as `Milliseconds`, or changing the
    `snowscrape/{stage}` namespace silently blinds an alarm; and
  - the module is fail-open by design -- `put_metric` and `emit_batch_metrics`
    must SWALLOW any CloudWatch error so a telemetry hiccup never fails the
    request it is measuring. A regression turning either into a raising path
    would take down the live path it is only supposed to observe.

There are also several quiet load-bearing rules: `emit_crawl_success_rate` emits
NOTHING when `total_count == 0` (no divide, no metric), `emit_batch_metrics`
caps at the CloudWatch 20-metric-per-call limit (`metrics[:20]`) and skips the
API call entirely for an empty list, dimensions are attached ONLY when provided,
and both `get_cloudwatch_client` and `get_metrics_emitter` are module-level
singletons.

The module's only non-determinism is `boto3.client`, `os.environ`, and the wall
clock. Most tests construct an emitter whose `get_cloudwatch_client` is patched
to return a recording `FakeCloudWatch`, so the exact `put_metric_data` kwargs are
asserted without AWS; the singleton/region test drives the real
`get_cloudwatch_client` with a `boto3.client` recorder. The two module globals
are reset between tests by an autouse fixture.
"""
from datetime import datetime, timezone

import pytest

import metrics


@pytest.fixture(autouse=True)
def reset_metrics_singletons(monkeypatch):
    """Reset the module-level CloudWatch client + emitter between tests.

    `get_cloudwatch_client` caches its client in `_cloudwatch_client` and
    `get_metrics_emitter` caches the emitter in `_metrics_emitter`; a value
    leaking across tests would mask the construction paths. Also clear the env
    vars the emitter reads at construction so each test starts from defaults.
    """
    monkeypatch.setattr(metrics, "_cloudwatch_client", None)
    monkeypatch.setattr(metrics, "_metrics_emitter", None)
    for key in ("REGION", "STAGE", "AWS_LAMBDA_FUNCTION_NAME"):
        monkeypatch.delenv(key, raising=False)
    yield
    metrics._cloudwatch_client = None
    metrics._metrics_emitter = None


class FakeCloudWatch:
    """Recording stand-in for the boto3 CloudWatch client.

    Captures every `put_metric_data` call's kwargs, or raises when `.error` is
    set so the fail-open swallow can be exercised.
    """

    def __init__(self):
        self.calls = []  # list of {'Namespace': ..., 'MetricData': [...]}
        self.error = None

    def put_metric_data(self, **kwargs):
        if self.error:
            raise self.error
        self.calls.append(kwargs)


@pytest.fixture
def emitter(monkeypatch):
    """A MetricsEmitter wired to a recording FakeCloudWatch.

    Patches `get_cloudwatch_client` (what `__init__` calls) so the construction
    wiring is genuinely exercised, and returns both the emitter and the fake so
    a test can read back the emitted metric data.
    """
    fake = FakeCloudWatch()
    monkeypatch.setattr(metrics, "get_cloudwatch_client", lambda: fake)
    em = metrics.MetricsEmitter()
    return em, fake


def _only_call(fake):
    """Assert exactly one put_metric_data call and return its single metric dict."""
    assert len(fake.calls) == 1
    data = fake.calls[0]["MetricData"]
    assert len(data) == 1
    return fake.calls[0], data[0]


# --------------------------------------------------------------------------
# get_cloudwatch_client: singleton + region
# --------------------------------------------------------------------------

class TestGetCloudwatchClient:
    def test_creates_client_with_default_region(self, monkeypatch):
        captured = {}

        def fake_boto_client(service, region_name=None):
            captured["service"] = service
            captured["region_name"] = region_name
            return object()

        monkeypatch.setattr(metrics.boto3, "client", fake_boto_client)
        client = metrics.get_cloudwatch_client()
        assert client is not None
        assert captured == {"service": "cloudwatch", "region_name": "us-east-2"}

    def test_honors_region_env_override(self, monkeypatch):
        captured = {}
        monkeypatch.setenv("REGION", "eu-west-1")

        def fake_boto_client(service, region_name=None):
            captured["region_name"] = region_name
            return object()

        monkeypatch.setattr(metrics.boto3, "client", fake_boto_client)
        metrics.get_cloudwatch_client()
        assert captured["region_name"] == "eu-west-1"

    def test_caches_singleton(self, monkeypatch):
        calls = []

        def fake_boto_client(service, region_name=None):
            calls.append(service)
            return object()

        monkeypatch.setattr(metrics.boto3, "client", fake_boto_client)
        first = metrics.get_cloudwatch_client()
        second = metrics.get_cloudwatch_client()
        assert first is second
        assert calls == ["cloudwatch"]  # built exactly once


# --------------------------------------------------------------------------
# MetricsEmitter.__init__: namespace + identity from env
# --------------------------------------------------------------------------

class TestEmitterInit:
    def test_defaults(self, monkeypatch):
        fake = FakeCloudWatch()
        monkeypatch.setattr(metrics, "get_cloudwatch_client", lambda: fake)
        em = metrics.MetricsEmitter()
        assert em.cloudwatch is fake
        assert em.service == "snowscrape"
        assert em.stage == "dev"
        assert em.namespace == "snowscrape/dev"

    def test_namespace_tracks_stage(self, monkeypatch):
        fake = FakeCloudWatch()
        monkeypatch.setattr(metrics, "get_cloudwatch_client", lambda: fake)
        monkeypatch.setenv("STAGE", "prod")
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "snowscrape-prod-JobQueue")
        em = metrics.MetricsEmitter()
        assert em.stage == "prod"
        assert em.namespace == "snowscrape/prod"
        assert em.service == "snowscrape-prod-JobQueue"


# --------------------------------------------------------------------------
# put_metric: shape, defaults, dimensions, fail-open
# --------------------------------------------------------------------------

class TestPutMetric:
    def test_basic_shape_and_namespace(self, emitter):
        em, fake = emitter
        em.put_metric("Foo", 42, "Count", [{"Name": "JobId", "Value": "j1"}])
        call, metric = _only_call(fake)
        assert call["Namespace"] == "snowscrape/dev"
        assert metric["MetricName"] == "Foo"
        assert metric["Value"] == 42
        assert metric["Unit"] == "Count"
        assert metric["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]

    def test_unit_defaults_to_none_string(self, emitter):
        em, fake = emitter
        em.put_metric("Foo", 1)
        _, metric = _only_call(fake)
        assert metric["Unit"] == "None"

    def test_timestamp_is_utc_aware_datetime(self, emitter):
        em, fake = emitter
        em.put_metric("Foo", 1)
        _, metric = _only_call(fake)
        ts = metric["Timestamp"]
        assert isinstance(ts, datetime)
        assert ts.tzinfo == timezone.utc

    def test_dimensions_omitted_when_not_provided(self, emitter):
        em, fake = emitter
        em.put_metric("Foo", 1, "Count")
        _, metric = _only_call(fake)
        assert "Dimensions" not in metric

    def test_dimensions_omitted_when_empty_list(self, emitter):
        # `if dimensions:` treats [] as falsy, so an empty list is NOT attached.
        em, fake = emitter
        em.put_metric("Foo", 1, "Count", [])
        _, metric = _only_call(fake)
        assert "Dimensions" not in metric

    def test_swallows_cloudwatch_error(self, emitter):
        em, fake = emitter
        fake.error = RuntimeError("CloudWatch throttled")
        # Must not raise: telemetry failure never breaks the measured request.
        em.put_metric("Foo", 1, "Count")
        assert fake.calls == []

    def test_namespace_uses_stage(self, monkeypatch):
        # The `snowscrape/{stage}` namespace must actually reach put_metric_data,
        # not just be set as an attribute.
        fake = FakeCloudWatch()
        monkeypatch.setattr(metrics, "get_cloudwatch_client", lambda: fake)
        monkeypatch.setenv("STAGE", "prod")
        em = metrics.MetricsEmitter()
        em.put_metric("Foo", 1, "Count")
        assert fake.calls[0]["Namespace"] == "snowscrape/prod"


# --------------------------------------------------------------------------
# emit_* helpers: each pins metric name / value / unit / dimensions
# --------------------------------------------------------------------------

def _metrics_by_name(fake):
    """Flatten all emitted metric dicts across calls, keyed by MetricName."""
    out = {}
    for call in fake.calls:
        for m in call["MetricData"]:
            out[m["MetricName"]] = m
    return out


class TestEmitHelpers:
    def test_emit_crawl_success(self, emitter):
        em, fake = emitter
        em.emit_crawl_success("j1", "https://x", 1234.5)
        assert len(fake.calls) == 2  # two separate put_metric_data calls
        by_name = _metrics_by_name(fake)
        assert by_name["CrawlSuccess"]["Value"] == 1
        assert by_name["CrawlSuccess"]["Unit"] == "Count"
        assert by_name["CrawlSuccess"]["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]
        assert by_name["CrawlDuration"]["Value"] == 1234.5
        assert by_name["CrawlDuration"]["Unit"] == "Milliseconds"
        assert by_name["CrawlDuration"]["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]

    def test_emit_crawl_failure_carries_error_type_dimension(self, emitter):
        em, fake = emitter
        em.emit_crawl_failure("j1", "https://x", "timeout")
        _, metric = _only_call(fake)
        assert metric["MetricName"] == "CrawlFailure"
        assert metric["Value"] == 1
        assert metric["Unit"] == "Count"
        assert metric["Dimensions"] == [
            {"Name": "JobId", "Value": "j1"},
            {"Name": "ErrorType", "Value": "timeout"},
        ]

    def test_emit_job_processing_duration(self, emitter):
        em, fake = emitter
        em.emit_job_processing_duration("j1", 5000.0, "completed")
        _, metric = _only_call(fake)
        assert metric["MetricName"] == "JobProcessingDuration"
        assert metric["Value"] == 5000.0
        assert metric["Unit"] == "Milliseconds"
        assert metric["Dimensions"] == [
            {"Name": "JobId", "Value": "j1"},
            {"Name": "Status", "Value": "completed"},
        ]

    def test_emit_urls_processed(self, emitter):
        em, fake = emitter
        em.emit_urls_processed("j1", 17)
        _, metric = _only_call(fake)
        assert metric["MetricName"] == "UrlsProcessed"
        assert metric["Value"] == 17
        assert metric["Unit"] == "Count"
        assert metric["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]

    def test_emit_job_queue_depth_has_no_dimensions(self, emitter):
        em, fake = emitter
        em.emit_job_queue_depth(9)
        _, metric = _only_call(fake)
        assert metric["MetricName"] == "JobQueueDepth"
        assert metric["Value"] == 9
        assert metric["Unit"] == "Count"
        assert "Dimensions" not in metric

    def test_emit_crawl_success_rate_computes_percent(self, emitter):
        em, fake = emitter
        em.emit_crawl_success_rate("j1", 3, 4)
        _, metric = _only_call(fake)
        assert metric["MetricName"] == "CrawlSuccessRate"
        assert metric["Value"] == 75.0
        assert metric["Unit"] == "Percent"
        assert metric["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]

    def test_emit_crawl_success_rate_zero_total_emits_nothing(self, emitter):
        # `if total_count > 0:` guards the divide AND the emit; 0 total is a
        # silent no-op (no DivisionByZero, no metric).
        em, fake = emitter
        em.emit_crawl_success_rate("j1", 0, 0)
        assert fake.calls == []

    def test_emit_job_created_emits_two_metrics(self, emitter):
        em, fake = emitter
        em.emit_job_created("j1", 50)
        assert len(fake.calls) == 2  # two separate put_metric_data calls
        by_name = _metrics_by_name(fake)
        assert by_name["JobCreated"]["Value"] == 1
        assert by_name["JobCreated"]["Unit"] == "Count"
        assert by_name["JobUrlCount"]["Value"] == 50
        assert by_name["JobUrlCount"]["Unit"] == "Count"
        for name in ("JobCreated", "JobUrlCount"):
            assert by_name[name]["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]

    def test_emit_query_execution(self, emitter):
        em, fake = emitter
        em.emit_query_execution("j1", "xpath", 12.0, 8)
        assert len(fake.calls) == 2  # two separate put_metric_data calls
        by_name = _metrics_by_name(fake)
        assert by_name["QueryExecutionDuration"]["Value"] == 12.0
        assert by_name["QueryExecutionDuration"]["Unit"] == "Milliseconds"
        assert by_name["QueryResultCount"]["Value"] == 8
        assert by_name["QueryResultCount"]["Unit"] == "Count"
        expected_dims = [
            {"Name": "JobId", "Value": "j1"},
            {"Name": "QueryType", "Value": "xpath"},
        ]
        assert by_name["QueryExecutionDuration"]["Dimensions"] == expected_dims
        assert by_name["QueryResultCount"]["Dimensions"] == expected_dims

    def test_emit_s3_upload(self, emitter):
        em, fake = emitter
        em.emit_s3_upload("j1", 2048, 33.0)
        assert len(fake.calls) == 2  # two separate put_metric_data calls
        by_name = _metrics_by_name(fake)
        assert by_name["S3UploadSize"]["Value"] == 2048
        assert by_name["S3UploadSize"]["Unit"] == "Bytes"
        assert by_name["S3UploadDuration"]["Value"] == 33.0
        assert by_name["S3UploadDuration"]["Unit"] == "Milliseconds"
        for name in ("S3UploadSize", "S3UploadDuration"):
            assert by_name[name]["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]


# --------------------------------------------------------------------------
# emit_batch_metrics: single call, 20-cap, unit/dim defaults, fail-open
# --------------------------------------------------------------------------

class TestEmitBatchMetrics:
    def test_single_put_call_with_all_metrics(self, emitter):
        em, fake = emitter
        em.emit_batch_metrics([
            {"name": "A", "value": 1, "unit": "Count",
             "dimensions": [{"Name": "JobId", "Value": "j1"}]},
            {"name": "B", "value": 2.5, "unit": "Milliseconds"},
        ])
        assert len(fake.calls) == 1
        call = fake.calls[0]
        assert call["Namespace"] == "snowscrape/dev"
        data = call["MetricData"]
        assert [m["MetricName"] for m in data] == ["A", "B"]
        assert data[0]["Dimensions"] == [{"Name": "JobId", "Value": "j1"}]
        assert "Dimensions" not in data[1]

    def test_unit_defaults_to_none_string(self, emitter):
        em, fake = emitter
        em.emit_batch_metrics([{"name": "A", "value": 1}])
        metric = fake.calls[0]["MetricData"][0]
        assert metric["Unit"] == "None"

    def test_each_metric_gets_utc_timestamp(self, emitter):
        em, fake = emitter
        em.emit_batch_metrics([{"name": "A", "value": 1}])
        ts = fake.calls[0]["MetricData"][0]["Timestamp"]
        assert isinstance(ts, datetime)
        assert ts.tzinfo == timezone.utc

    def test_caps_at_twenty(self, emitter):
        em, fake = emitter
        em.emit_batch_metrics([{"name": f"M{i}", "value": i} for i in range(25)])
        data = fake.calls[0]["MetricData"]
        assert len(data) == 20
        assert [m["MetricName"] for m in data] == [f"M{i}" for i in range(20)]

    def test_empty_list_makes_no_call(self, emitter):
        # `if metric_data:` guards the put, so an empty batch is a no-op.
        em, fake = emitter
        em.emit_batch_metrics([])
        assert fake.calls == []

    def test_swallows_cloudwatch_error(self, emitter):
        em, fake = emitter
        fake.error = RuntimeError("CloudWatch down")
        em.emit_batch_metrics([{"name": "A", "value": 1}])
        assert fake.calls == []

    def test_swallows_malformed_metric_dict(self, emitter):
        # The metric-building loop runs inside the same try/except, so a dict
        # missing the required `name`/`value` key raises a KeyError that is
        # swallowed rather than propagated (fail-open).
        em, fake = emitter
        em.emit_batch_metrics([{"value": 1}])  # no 'name'
        assert fake.calls == []


# --------------------------------------------------------------------------
# get_metrics_emitter: singleton
# --------------------------------------------------------------------------

class TestGetMetricsEmitter:
    def test_caches_singleton(self, monkeypatch):
        monkeypatch.setattr(metrics, "get_cloudwatch_client", lambda: FakeCloudWatch())
        first = metrics.get_metrics_emitter()
        second = metrics.get_metrics_emitter()
        assert first is second
        assert isinstance(first, metrics.MetricsEmitter)
