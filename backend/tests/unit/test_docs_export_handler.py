"""Characterization tests for docs_export_handler's helpers and SQS batch semantics.

These pin down the CURRENT behavior of the granular units in
``docs_export_handler.py`` that the end-to-end integration test
(``tests/integration/test_docs_export_flow.py``) does not exercise directly:

- ``_render_doc_title`` template substitution (job name, date, edge cases)
- ``_row_label`` precedence (title -> url -> "Row N")
- ``_read_results`` S3 payload-shape handling (list vs ``{"rows": [...]}``)
- ``_log_export`` DynamoDB row shape, defaults, error truncation, and TTL
- the ``MAX_DOCS_PER_ROW_RUN`` cap constant
- ``docs_export_handler`` SQS partial-batch-response semantics

No source behavior is changed; these document existing behavior so future
refactors stay honest.
"""
import json
import time
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

import docs_export_handler as deh


def _fixed_dt(date_str):
    """A datetime stand-in whose now(...).strftime(...) returns date_str."""
    fake = MagicMock()
    fake.now.return_value.strftime.return_value = date_str
    return fake


# --------------------------------------------------------------------------- #
# _render_doc_title
# --------------------------------------------------------------------------- #

def test_render_doc_title_replaces_job_name_and_date():
    with patch.object(deh, "datetime", _fixed_dt("2026-06-18")):
        out = deh._render_doc_title("{{job_name}} — {{date}}", "My Job")
    assert out == "My Job — 2026-06-18"


def test_render_doc_title_formats_date_as_iso_day():
    fake = _fixed_dt("2026-06-18")
    with patch.object(deh, "datetime", fake):
        deh._render_doc_title("{{date}}", "x")
    fake.now.assert_called_once_with(deh.timezone.utc)
    fake.now.return_value.strftime.assert_called_once_with("%Y-%m-%d")


def test_render_doc_title_empty_job_name_becomes_blank_not_none():
    with patch.object(deh, "datetime", _fixed_dt("2026-06-18")):
        out = deh._render_doc_title("[{{job_name}}]", "")
    assert out == "[]"


def test_render_doc_title_none_job_name_becomes_blank():
    with patch.object(deh, "datetime", _fixed_dt("2026-06-18")):
        out = deh._render_doc_title("[{{job_name}}]", None)
    assert out == "[]"


def test_render_doc_title_without_placeholders_is_unchanged():
    with patch.object(deh, "datetime", _fixed_dt("2026-06-18")):
        out = deh._render_doc_title("static name", "Job")
    assert out == "static name"


def test_render_doc_title_replaces_every_job_name_occurrence():
    with patch.object(deh, "datetime", _fixed_dt("2026-06-18")):
        out = deh._render_doc_title("{{job_name}}/{{job_name}}", "J")
    assert out == "J/J"


# --------------------------------------------------------------------------- #
# _row_label
# --------------------------------------------------------------------------- #

def test_row_label_prefers_title():
    assert deh._row_label({"title": "T", "url": "https://u"}, 0) == "T"


def test_row_label_falls_back_to_url_when_title_missing():
    assert deh._row_label({"url": "https://u"}, 0) == "https://u"


def test_row_label_treats_empty_title_as_missing():
    assert deh._row_label({"title": "", "url": "https://u"}, 3) == "https://u"


def test_row_label_falls_back_to_one_based_row_index():
    assert deh._row_label({}, 0) == "Row 1"
    assert deh._row_label({"title": "", "url": ""}, 4) == "Row 5"


def test_row_label_coerces_non_string_title():
    assert deh._row_label({"title": 123}, 0) == "123"


# --------------------------------------------------------------------------- #
# MAX_DOCS_PER_ROW_RUN
# --------------------------------------------------------------------------- #

def test_max_docs_per_row_run_is_25():
    assert deh.MAX_DOCS_PER_ROW_RUN == 25


# --------------------------------------------------------------------------- #
# _read_results / _log_export (need mocked S3 + DynamoDB)
# --------------------------------------------------------------------------- #

@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-2")
    monkeypatch.setenv("S3_BUCKET", "results-unit-test")
    monkeypatch.setenv("DYNAMODB_DOCS_EXPORTS_TABLE", "DocsExports-unit-test")
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-2")
        s3.create_bucket(
            Bucket="results-unit-test",
            CreateBucketConfiguration={"LocationConstraint": "us-east-2"},
        )
        dynamo = boto3.resource("dynamodb", region_name="us-east-2")
        dynamo.create_table(
            TableName="DocsExports-unit-test",
            KeySchema=[{"AttributeName": "export_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "export_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield {"s3": s3, "dynamo": dynamo}


def _put_results(s3, key, payload):
    s3.put_object(
        Bucket="results-unit-test",
        Key=key,
        Body=json.dumps(payload).encode("utf-8"),
    )


def test_read_results_returns_plain_list_as_is(aws):
    _put_results(aws["s3"], "k/list.json", [{"a": 1}, {"a": 2}])
    assert deh._read_results("k/list.json") == [{"a": 1}, {"a": 2}]


def test_read_results_unwraps_rows_key(aws):
    _put_results(aws["s3"], "k/wrapped.json", {"rows": [{"a": 1}], "meta": "ignored"})
    assert deh._read_results("k/wrapped.json") == [{"a": 1}]


def test_read_results_dict_without_rows_is_empty(aws):
    _put_results(aws["s3"], "k/norows.json", {"meta": "only"})
    assert deh._read_results("k/norows.json") == []


def _get_export(aws, export_id):
    return aws["dynamo"].Table("DocsExports-unit-test").get_item(
        Key={"export_id": export_id}
    )["Item"]


def test_log_export_writes_full_row(aws):
    deh._log_export("exp-1", "success", doc_id="doc-9", doc_url="https://d", doc_count=3)
    item = _get_export(aws, "exp-1")
    assert item["status"] == "success"
    assert item["doc_id"] == "doc-9"
    assert item["doc_url"] == "https://d"
    assert int(item["doc_count"]) == 3
    assert item["error"] == ""
    assert "T" in item["created_at"]
    assert int(item["ttl"]) > int(item["timestamp"])


def test_log_export_defaults_for_optional_fields(aws):
    deh._log_export("exp-2", "failed")
    item = _get_export(aws, "exp-2")
    assert item["doc_id"] == ""
    assert item["doc_url"] == ""
    assert int(item["doc_count"]) == 0
    assert item["error"] == ""


def test_log_export_truncates_error_to_1000_chars(aws):
    deh._log_export("exp-3", "failed", error="x" * 2000)
    item = _get_export(aws, "exp-3")
    assert len(item["error"]) == 1000


def test_log_export_ttl_is_90_days_after_timestamp(aws):
    deh._log_export("exp-4", "success")
    item = _get_export(aws, "exp-4")
    delta = int(item["ttl"]) - int(item["timestamp"])
    # ttl and timestamp are taken from two near-simultaneous time.time() calls.
    assert abs(delta - 60 * 60 * 24 * 90) <= 2


# --------------------------------------------------------------------------- #
# docs_export_handler — SQS partial batch responses
# --------------------------------------------------------------------------- #

def test_handler_empty_event_returns_no_failures():
    assert deh.docs_export_handler({"Records": []}, None) == {"batchItemFailures": []}
    assert deh.docs_export_handler({}, None) == {"batchItemFailures": []}


def test_handler_returns_only_failed_records_in_a_mixed_batch():
    ok = {"messageId": "m-ok", "body": json.dumps({"export_id": "ok"})}
    bad = {"messageId": "m-bad", "body": json.dumps({"export_id": "boom"})}

    def proc_side(message):
        if message["export_id"] == "boom":
            raise RuntimeError("boom error")

    with patch.object(deh, "_process_one", side_effect=proc_side), \
            patch.object(deh, "_log_export") as log:
        result = deh.docs_export_handler({"Records": [ok, bad]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "m-bad"}]}
    log.assert_called_once()
    assert log.call_args.args[0] == "boom"
    assert log.call_args.args[1] == "failed"


def test_handler_failure_log_falls_back_to_message_id_without_export_id():
    rec = {"messageId": "m-7", "body": json.dumps({"destination_id": "d"})}
    with patch.object(deh, "_process_one", side_effect=RuntimeError("err")), \
            patch.object(deh, "_log_export") as log:
        result = deh.docs_export_handler({"Records": [rec]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "m-7"}]}
    assert log.call_args.args[0] == "m-7"
    assert log.call_args.args[1] == "failed"


def test_handler_unparseable_body_reports_failure_without_logging():
    rec = {"messageId": "m-bad", "body": "{not valid json"}
    with patch.object(deh, "_log_export") as log:
        result = deh.docs_export_handler({"Records": [rec]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "m-bad"}]}
    # Both json.loads attempts fail, so the export log is never written.
    log.assert_not_called()
