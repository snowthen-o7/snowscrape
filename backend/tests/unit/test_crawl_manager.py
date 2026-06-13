"""Unit tests for crawl_manager: the query-execution dispatch engine.

`crawl_manager.process_queries` is the live extraction chokepoint: every scraped
page (HTML, JSON, or PDF, plus Firecrawl markdown) is handed here with a list of
user-defined queries, and it dispatches each to the right extractor (xpath /
regex / jsonpath / pdf_* / ai), applies the optional pipe-join, and isolates a
failing query so one bad selector never sinks the whole crawl. It had ZERO
dedicated coverage despite being on every successful scrape. A silent regression
here is a correctness/data-loss bug: a whole query type quietly returning None,
the join contract changing, or one query's exception aborting the batch.

These are characterization tests (no source change). The query extractors lean
on third-party parsers (lxml, jsonpath_ng) which are exercised for real; the
PDF/AI helpers and the signal-based regex runner are isolated behind monkeypatch
so the dispatch + join + error-isolation logic is pinned deterministically and
cross-platform (`safe_regex_findall` uses signal.SIGALRM, which only exists on
Unix/Lambda, so its own tests are skipped off-Unix).

`get_crawl` reads the URLs DynamoDB table; it is covered against moto by pointing
the module-level `dynamodb` resource at the mocked one.
"""
import importlib.util
import signal

import pytest

import crawl_manager
from crawl_manager import process_queries, safe_regex_findall, RegexTimeoutError


HTML = b"""
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Sample Product</h1>
    <div class="price">$99.99</div>
    <ul id="features"><li>One</li><li>Two</li><li>Three</li></ul>
</body>
</html>
"""

JSON = b'{"product": {"name": "Widget", "price": 9.99, "tags": ["a", "b"]}}'

HAS_SIGALRM = hasattr(signal, "SIGALRM")
# ai_extractor.py does an unconditional top-level `import anthropic` (a declared
# backend dep, present under `uv sync`), so the AI tests below skip rather than
# error in a partial environment that lacks it.
HAS_ANTHROPIC = importlib.util.find_spec("anthropic") is not None


# --------------------------------------------------------------------------- #
# process_queries: xpath
# --------------------------------------------------------------------------- #
class TestProcessQueriesXpath:
    def test_xpath_extracts_text_nodes_as_strings(self):
        out = process_queries(HTML, [{"name": "title", "type": "xpath", "query": "//title/text()"}])
        assert out == {"title": ["Test Page"]}

    def test_xpath_multiple_results_returned_as_list(self):
        out = process_queries(HTML, [{"name": "feat", "type": "xpath", "query": "//ul[@id='features']/li/text()"}])
        assert out == {"feat": ["One", "Two", "Three"]}

    def test_xpath_join_true_pipe_concatenates(self):
        out = process_queries(
            HTML,
            [{"name": "feat", "type": "xpath", "query": "//ul[@id='features']/li/text()", "join": True}],
        )
        assert out == {"feat": "One|Two|Three"}

    def test_xpath_no_match_is_empty_list(self):
        out = process_queries(HTML, [{"name": "missing", "type": "xpath", "query": "//nope/text()"}])
        assert out == {"missing": []}

    def test_xpath_join_with_empty_results_stays_empty_list(self):
        # `join_flag and results` is falsy when results is empty, so the else
        # branch wins: an empty extraction is [] regardless of the join flag.
        out = process_queries(
            HTML, [{"name": "missing", "type": "xpath", "query": "//nope/text()", "join": True}]
        )
        assert out == {"missing": []}

    def test_invalid_xpath_expression_isolated_as_none(self):
        # A malformed XPath raises inside the per-query try; the handler must
        # swallow it and record None rather than aborting the whole batch.
        out = process_queries(HTML, [{"name": "bad", "type": "xpath", "query": "count("}])
        assert out == {"bad": None}

    def test_query_name_defaults_to_unnamed(self):
        out = process_queries(HTML, [{"type": "xpath", "query": "//title/text()"}])
        assert out == {"unnamed": ["Test Page"]}


# --------------------------------------------------------------------------- #
# process_queries: jsonpath
# --------------------------------------------------------------------------- #
class TestProcessQueriesJsonpath:
    def test_jsonpath_scalar(self):
        out = process_queries(JSON, [{"name": "price", "type": "jsonpath", "query": "$.product.price"}])
        assert out == {"price": [9.99]}

    def test_jsonpath_array_elements(self):
        out = process_queries(JSON, [{"name": "tags", "type": "jsonpath", "query": "$.product.tags[*]"}])
        assert out == {"tags": ["a", "b"]}

    def test_jsonpath_join_true(self):
        out = process_queries(
            JSON, [{"name": "tags", "type": "jsonpath", "query": "$.product.tags[*]", "join": True}]
        )
        assert out == {"tags": "a|b"}

    def test_jsonpath_on_non_json_isolated_as_none(self):
        # json.loads(HTML) raises; the per-query guard records None.
        out = process_queries(HTML, [{"name": "x", "type": "jsonpath", "query": "$.x"}])
        assert out == {"x": None}


# --------------------------------------------------------------------------- #
# process_queries: regex (safe_regex_findall isolated behind monkeypatch so the
# dispatch + join + timeout-handling is pinned without depending on SIGALRM)
# --------------------------------------------------------------------------- #
class TestProcessQueriesRegex:
    def test_regex_returns_findall_results(self, monkeypatch):
        monkeypatch.setattr(crawl_manager, "safe_regex_findall", lambda pat, text: ["19.99", "5.00"])
        out = process_queries(HTML, [{"name": "prices", "type": "regex", "query": r"\d+\.\d{2}"}])
        assert out == {"prices": ["19.99", "5.00"]}

    def test_regex_join_true(self, monkeypatch):
        monkeypatch.setattr(crawl_manager, "safe_regex_findall", lambda pat, text: ["19.99", "5.00"])
        out = process_queries(
            HTML, [{"name": "prices", "type": "regex", "query": r"\d+\.\d{2}", "join": True}]
        )
        assert out == {"prices": "19.99|5.00"}

    def test_regex_timeout_isolated_as_none(self, monkeypatch):
        def boom(pat, text):
            raise RegexTimeoutError("timed out")

        monkeypatch.setattr(crawl_manager, "safe_regex_findall", boom)
        out = process_queries(HTML, [{"name": "prices", "type": "regex", "query": r"(a+)+"}])
        assert out == {"prices": None}


# --------------------------------------------------------------------------- #
# process_queries: PDF query types (helpers isolated behind monkeypatch)
# --------------------------------------------------------------------------- #
class TestProcessQueriesPdf:
    def test_pdf_text_dispatches_to_handler_and_skips_join(self, monkeypatch):
        monkeypatch.setattr(crawl_manager, "is_pdf_content", lambda content, ct=None: True)
        # process_pdf_query owns its own join logic, so its return value is used
        # verbatim (even a string is not re-joined by process_queries).
        monkeypatch.setattr(crawl_manager, "process_pdf_query", lambda content, q: "extracted text")
        out = process_queries(b"%PDF-1.4 fake", [{"name": "body", "type": "pdf_text", "query": None}])
        assert out == {"body": "extracted text"}

    def test_pdf_query_type_requires_no_expression(self, monkeypatch):
        # A None query expression is normally skipped, but pdf_* types are
        # explicitly exempt (they can extract all text/tables with no selector).
        monkeypatch.setattr(crawl_manager, "is_pdf_content", lambda content, ct=None: True)
        called = {}

        def fake_pdf(content, q):
            called["hit"] = True
            return ["row"]

        monkeypatch.setattr(crawl_manager, "process_pdf_query", fake_pdf)
        out = process_queries(b"%PDF", [{"name": "tbl", "type": "pdf_table"}])
        assert called.get("hit") is True
        assert out == {"tbl": ["row"]}

    def test_pdf_query_on_non_pdf_content_is_none(self, monkeypatch):
        monkeypatch.setattr(crawl_manager, "is_pdf_content", lambda content, ct=None: False)
        out = process_queries(HTML, [{"name": "body", "type": "pdf_text", "query": None}])
        assert out == {"body": None}

    def test_xpath_on_pdf_content_is_none(self, monkeypatch):
        # When content is a PDF, the HTML tree is never built, so an HTML query
        # type (xpath) cannot run and is recorded as None.
        monkeypatch.setattr(crawl_manager, "is_pdf_content", lambda content, ct=None: True)
        out = process_queries(b"%PDF", [{"name": "t", "type": "xpath", "query": "//title/text()"}])
        assert out == {"t": None}


# --------------------------------------------------------------------------- #
# process_queries: AI extraction (extract_with_ai imported lazily from
# ai_extractor inside the branch, so the source module attribute is patched)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAS_ANTHROPIC, reason="ai_extractor imports anthropic at module top")
class TestProcessQueriesAi:
    def test_ai_returns_fields_and_prefers_markdown(self, monkeypatch):
        import ai_extractor

        seen = {}

        def fake_extract(content, description, content_type=None):
            seen["content"] = content
            seen["content_type"] = content_type
            return {"fields": {"name": "Widget", "price": "9.99"}}

        monkeypatch.setattr(ai_extractor, "extract_with_ai", fake_extract)
        out = process_queries(
            HTML,
            [{"name": "data", "type": "ai", "query": "the product name and price"}],
            markdown_content="# Widget\nprice 9.99",
        )
        assert out == {"data": {"name": "Widget", "price": "9.99"}}
        # Markdown is preferred over the raw page content when present.
        assert seen["content"] == "# Widget\nprice 9.99"
        assert seen["content_type"] == "markdown"

    def test_ai_falls_back_to_decoded_html_when_no_markdown(self, monkeypatch):
        import ai_extractor

        seen = {}

        def fake_extract(content, description, content_type=None):
            seen["content_type"] = content_type
            return {"fields": {"ok": True}}

        monkeypatch.setattr(ai_extractor, "extract_with_ai", fake_extract)
        out = process_queries(HTML, [{"name": "data", "type": "ai", "query": "anything"}])
        assert out == {"data": {"ok": True}}
        assert seen["content_type"] == "html"

    def test_ai_failure_isolated_as_none(self, monkeypatch):
        import ai_extractor

        def boom(content, description, content_type=None):
            raise RuntimeError("model unavailable")

        monkeypatch.setattr(ai_extractor, "extract_with_ai", boom)
        out = process_queries(HTML, [{"name": "data", "type": "ai", "query": "anything"}])
        assert out == {"data": None}


# --------------------------------------------------------------------------- #
# process_queries: dispatch-level contracts
# --------------------------------------------------------------------------- #
class TestProcessQueriesDispatch:
    def test_empty_query_list_returns_empty_dict(self):
        assert process_queries(HTML, []) == {}

    def test_unknown_query_type_is_none(self):
        out = process_queries(HTML, [{"name": "weird", "type": "css", "query": "div"}])
        assert out == {"weird": None}

    def test_missing_expression_for_html_type_is_skipped(self):
        # A non-PDF query with no `query` expression is skipped entirely, so its
        # name never appears in the result (distinct from being recorded None).
        out = process_queries(HTML, [{"name": "skipme", "type": "xpath"}])
        assert out == {}

    def test_multiple_queries_processed_independently(self, monkeypatch):
        monkeypatch.setattr(crawl_manager, "safe_regex_findall", lambda pat, text: ["m"])
        queries = [
            {"name": "title", "type": "xpath", "query": "//title/text()"},
            {"name": "price", "type": "jsonpath", "query": "$.x"},  # JSON parse fails on HTML -> None
            {"name": "rx", "type": "regex", "query": "m"},
        ]
        out = process_queries(HTML, queries)
        assert out == {"title": ["Test Page"], "price": None, "rx": ["m"]}


# --------------------------------------------------------------------------- #
# safe_regex_findall: SIGALRM-based, so only meaningful on Unix/Lambda
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAS_SIGALRM, reason="signal.SIGALRM is Unix-only (absent on Windows)")
class TestSafeRegexFindall:
    def test_returns_matches_within_timeout(self):
        assert safe_regex_findall(r"\d+", "a1b22c333") == ["1", "22", "333"]

    def test_no_match_returns_empty_list(self):
        assert safe_regex_findall(r"\d+", "no digits here") == []

    def test_invalid_pattern_raises_re_error(self):
        import re

        with pytest.raises(re.error):
            safe_regex_findall(r"(unterminated", "text")


# --------------------------------------------------------------------------- #
# get_crawl: DynamoDB URLs-table read (moto)
# --------------------------------------------------------------------------- #
class TestGetCrawl:
    def test_found_item_is_mapped_with_defaults(self, dynamodb_client, monkeypatch):
        # Point the module-level resource at the moto one so get_item is mocked.
        monkeypatch.setattr(crawl_manager, "dynamodb", dynamodb_client)
        url_table = dynamodb_client.Table("SnowscrapeUrls-test")
        url_table.put_item(
            Item={
                "job_id": "job-1",
                "url": "https://example.com/p1",
                "state": "completed",
                "attempts": 2,
                "http_code": 200,
                "results": {"title": ["Hi"]},
            }
        )
        out = crawl_manager.get_crawl("job-1", "https://example.com/p1")
        assert out == {
            "job_id": "job-1",
            "url": "https://example.com/p1",
            "state": "completed",
            "attempts": 2,
            "last_crawled": None,
            "error": None,
            "http_code": 200,
            "results": {"title": ["Hi"]},
        }

    def test_missing_optional_fields_get_defaults(self, dynamodb_client, monkeypatch):
        monkeypatch.setattr(crawl_manager, "dynamodb", dynamodb_client)
        url_table = dynamodb_client.Table("SnowscrapeUrls-test")
        url_table.put_item(Item={"job_id": "job-2", "url": "u2"})
        out = crawl_manager.get_crawl("job-2", "u2")
        assert out["state"] == "unknown"
        assert out["attempts"] == 0
        assert out["results"] == {}
        assert out["error"] is None

    def test_not_found_returns_none(self, dynamodb_client, monkeypatch):
        monkeypatch.setattr(crawl_manager, "dynamodb", dynamodb_client)
        assert crawl_manager.get_crawl("nope", "nope") is None

    def test_get_item_error_returns_none(self, monkeypatch):
        # The try/except guards the get_item call specifically, so a query
        # failure degrades to None rather than raising. (Note: the table
        # resolution + env read on the line above the try are NOT guarded, so
        # this pins only the get_item failure path, which is the live one once
        # the Lambda env is populated.)
        monkeypatch.setenv("DYNAMODB_URLS_TABLE", "SnowscrapeUrls-test")

        class BoomTable:
            def get_item(self, **kwargs):
                raise RuntimeError("dynamo down")

        class FakeResource:
            def Table(self, name):
                return BoomTable()

        monkeypatch.setattr(crawl_manager, "dynamodb", FakeResource())
        assert crawl_manager.get_crawl("j", "u") is None
