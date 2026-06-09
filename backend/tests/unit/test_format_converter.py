"""Unit tests for FormatConverter (pandas-free export: CSV / SQL / XLSX / Parquet).

These tests run in an environment WITHOUT pandas (matching the prod Lambda),
which is the whole point of issue #32: the previous module-top `import pandas`
made every non-JSON export crash with ModuleNotFoundError. Simply importing this
module and exercising CSV/SQL here proves the pandas-free rewrite.

S3 is mocked with moto; the converter resolves its client lazily via
connection_pool.get_s3_client(), so the global client cache is reset per test.
"""
import csv
import io
import json

import boto3
import pytest
from moto import mock_aws

import connection_pool

BUCKET = "snowscrape-results-test"  # matches pytest.ini S3_BUCKET


@pytest.fixture
def s3():
    """Fresh moto S3 with the results bucket, and a reset connection-pool cache."""
    connection_pool._s3_client = None
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client
    connection_pool._s3_client = None


def _make(results, job_id="abcd1234efff", flatten=False):
    from format_converter import FormatConverter

    conv = FormatConverter(job_id, results, BUCKET)
    conv.prepare_dataframe(flatten=flatten)
    return conv


def _get_body(s3_client, key):
    return s3_client.get_object(Bucket=BUCKET, Key=key)["Body"].read()


def _get_meta(s3_client, key):
    return s3_client.head_object(Bucket=BUCKET, Key=key)["Metadata"]


# ---------------------------------------------------------------------------
# Regression guard: the module imports and works with NO pandas present.
# ---------------------------------------------------------------------------

def test_module_imports_without_pandas():
    import sys

    # pandas is intentionally absent in this env (and in the Lambda).
    assert "pandas" not in sys.modules
    import format_converter  # must not raise

    assert hasattr(format_converter, "FormatConverter")


# ---------------------------------------------------------------------------
# prepare_dataframe (row/column normalization)
# ---------------------------------------------------------------------------

def test_prepare_flatten_builds_url_status_and_data_columns():
    results = [
        {"url": "http://a", "status": "ok", "http_code": 200,
         "data": {"title": "T1", "tags": ["x", "y"]}},
        {"url": "http://b", "status": "ok", "http_code": 200,
         "data": {"title": "T2"}},
    ]
    conv = _make(results, flatten=True)
    assert conv.columns == ["url", "status", "http_code", "title", "tags"]
    assert conv.rows[0]["tags"] == ["x", "y"]
    assert conv.rows[1].get("tags") is None  # second row had no tags key


def test_prepare_non_flatten_uses_first_seen_column_union():
    results = [
        {"a": 1, "b": 2},
        {"b": 3, "c": 4},  # introduces c after a/b
    ]
    conv = _make(results, flatten=False)
    assert conv.columns == ["a", "b", "c"]


def test_prepare_empty_results():
    conv = _make([], flatten=True)
    assert conv.rows == []
    assert conv.columns == []


def test_non_dict_rows_are_ignored():
    conv = _make(["not-a-dict", {"a": 1}, None], flatten=False)
    assert conv.rows == [{"a": 1}]
    assert conv.columns == ["a"]


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def test_csv_roundtrip(s3):
    results = [
        {"url": "http://a", "status": "ok", "http_code": 200,
         "data": {"title": "Hello", "tags": ["x", "y"], "meta": {"k": "v"}, "missing": None}},
    ]
    conv = _make(results, flatten=True)
    conv.convert_to_csv("jobs/j/result.csv")

    body = _get_body(s3, "jobs/j/result.csv").decode("utf-8")
    reader = list(csv.DictReader(io.StringIO(body)))
    assert len(reader) == 1
    row = reader[0]
    assert row["url"] == "http://a"
    assert row["title"] == "Hello"
    assert row["tags"] == "x|y"               # list -> pipe-joined
    assert row["meta"] == json.dumps({"k": "v"}, ensure_ascii=False, sort_keys=True)  # dict -> JSON
    assert row["missing"] == ""               # None -> empty


def test_csv_metadata_row_count(s3):
    conv = _make([{"a": 1}, {"a": 2}, {"a": 3}], flatten=False)
    conv.convert_to_csv("jobs/j/result.csv")
    assert _get_meta(s3, "jobs/j/result.csv")["row-count"] == "3"


def test_csv_without_explicit_prepare_flattens(s3):
    """If the handler skipped prepare, convert_* still works (auto-flatten)."""
    from format_converter import FormatConverter

    conv = FormatConverter("j", [{"url": "http://a", "data": {"x": "1"}}], BUCKET)
    conv.convert_to_csv("jobs/j/result.csv")  # no prepare_dataframe() called
    body = _get_body(s3, "jobs/j/result.csv").decode("utf-8")
    assert "url" in body.splitlines()[0]
    assert "x" in body.splitlines()[0]


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

def test_sql_create_table_and_insert_with_null_and_escaping(s3):
    results = [
        {"name": "O'Brien", "note": None},
        {"name": "plain", "note": "ok"},
    ]
    conv = _make(results, flatten=False)
    conv.convert_to_sql("jobs/j/result.sql", table_name="t")

    sql = _get_body(s3, "jobs/j/result.sql").decode("utf-8")
    assert "CREATE TABLE IF NOT EXISTS `t` (`name` TEXT, `note` TEXT);" in sql
    assert "INSERT INTO `t` (`name`, `note`) VALUES" in sql
    assert "'O''Brien'" in sql   # single quote doubled
    assert "NULL" in sql         # None -> NULL (not '')


def test_sql_escapes_backticks_in_column_identifiers(s3):
    """A scraped key containing a backtick must not break out of `identifier` quoting."""
    results = [{"col`); DROP TABLE x;--": "v"}]
    conv = _make(results, flatten=False)
    conv.convert_to_sql("jobs/j/result.sql", table_name="t")
    sql = _get_body(s3, "jobs/j/result.sql").decode("utf-8")
    # The backtick is doubled, so the injected text stays inside the identifier.
    assert "`col``); DROP TABLE x;--` TEXT" in sql
    assert "DROP TABLE x;--`" in sql  # still inside the quoted identifier, not bare


def test_sql_empty_results_emits_comment_not_invalid_ddl(s3):
    conv = _make([], flatten=False)
    conv.convert_to_sql("jobs/j/result.sql", table_name="t")
    sql = _get_body(s3, "jobs/j/result.sql").decode("utf-8")
    assert sql.startswith("-- No data to export")
    assert "()" not in sql  # no invalid zero-column CREATE TABLE


def test_sql_batches_in_groups_of_100(s3):
    results = [{"a": i} for i in range(150)]
    conv = _make(results, flatten=False)
    conv.convert_to_sql("jobs/j/result.sql", table_name="t")
    sql = _get_body(s3, "jobs/j/result.sql").decode("utf-8")
    # 150 rows -> two INSERT statements (100 + 50)
    assert sql.count("INSERT INTO `t`") == 2


# ---------------------------------------------------------------------------
# XLSX (openpyxl is bundled)
# ---------------------------------------------------------------------------

def test_xlsx_roundtrip(s3):
    openpyxl = pytest.importorskip("openpyxl")
    results = [
        {"url": "http://a", "status": "ok", "http_code": 200,
         "data": {"title": "Hello"}},
    ]
    conv = _make(results, flatten=True)
    conv.convert_to_xlsx("jobs/j/result.xlsx")

    body = _get_body(s3, "jobs/j/result.xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(body))
    ws = wb.active
    header = [c.value for c in ws[1]]
    assert header == ["url", "status", "http_code", "title"]
    assert ws.cell(row=2, column=1).value == "http://a"
    assert ws.cell(row=2, column=4).value == "Hello"
    assert _get_meta(s3, "jobs/j/result.xlsx")["format"] == "xlsx"


# ---------------------------------------------------------------------------
# Parquet (pyarrow intentionally NOT bundled -> clean, handled error)
# ---------------------------------------------------------------------------

def test_parquet_raises_clear_error_when_pyarrow_missing(s3):
    try:
        import pyarrow  # noqa: F401
        pytest.skip("pyarrow is installed; the missing-dep path is not exercised here")
    except ImportError:
        pass

    conv = _make([{"a": 1}], flatten=False)
    with pytest.raises(RuntimeError, match="pyarrow"):
        conv.convert_to_parquet("jobs/j/result.parquet")
