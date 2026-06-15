"""Unit tests for pdf_handler: the PDF extraction path of the scrape engine.

When a crawled URL serves a PDF, `crawl_manager` dispatches every `pdf_*` query
to `pdf_handler` (its tests treat this handler as an isolated black box). This
module is the only place the live scrape engine turns PDF bytes into structured
data, yet it had ZERO dedicated coverage. A silent regression here is a
correctness/data-loss bug: a query type quietly returning None, the pipe-join
contract changing, the table flatten/column-filter logic drifting, or one bad
query aborting the whole batch.

These are characterization tests (no source change). pdfplumber is a declared
backend dep (`pdfplumber==0.11.0`), but building real PDFs with known text and
tables is brittle, so `pdfplumber.open` is faked to return controllable pages.
That keeps the page-range math, cell cleaning, and metadata mapping deterministic
and fast. The `process_pdf_query` dispatch/regex/join/error-isolation logic is
pinned by patching the three `extract_pdf_*` helpers so only the dispatch layer
is under test.
"""
import io

import pdfplumber
import pytest

import pdf_handler
from pdf_handler import (
    extract_pdf_metadata,
    extract_pdf_tables,
    extract_pdf_text,
    is_pdf_content,
    process_pdf_queries,
    process_pdf_query,
)


# --------------------------------------------------------------------------- #
# Fake pdfplumber primitives
# --------------------------------------------------------------------------- #
class FakePage:
    """Stand-in for a pdfplumber Page."""

    def __init__(self, text=None, tables=None):
        self._text = text
        self._tables = tables if tables is not None else []
        self.extract_tables_calls = []

    def extract_text(self):
        return self._text

    def extract_tables(self, table_settings=None):
        self.extract_tables_calls.append(table_settings)
        return self._tables


class FakePdf:
    """Context-manager stand-in for a pdfplumber PDF."""

    def __init__(self, pages=None, metadata=None):
        self.pages = pages if pages is not None else []
        self.metadata = metadata

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def use_fake_pdf(monkeypatch):
    """Return a setter that makes `pdfplumber.open` yield the given FakePdf."""

    def _install(fake_pdf):
        opened = {}

        def _open(stream):
            opened["stream"] = stream
            return fake_pdf

        monkeypatch.setattr(pdfplumber, "open", _open)
        return opened

    return _install


# --------------------------------------------------------------------------- #
# is_pdf_content (pure)
# --------------------------------------------------------------------------- #
class TestIsPdfContent:
    def test_content_type_application_pdf_true(self):
        assert is_pdf_content(b"not really a pdf", "application/pdf") is True

    def test_content_type_is_case_insensitive_and_substring(self):
        assert is_pdf_content(b"x", "Application/PDF; charset=binary") is True

    def test_content_type_wins_before_magic_bytes_are_checked(self):
        # Garbage body but a PDF content-type still reports True.
        assert is_pdf_content(b"\x00\x01\x02\x03\x04", "application/pdf") is True

    def test_magic_bytes_detected_when_no_content_type(self):
        assert is_pdf_content(b"%PDF-1.7\n%binary", None) is True

    def test_magic_bytes_fallback_when_content_type_is_not_pdf(self):
        assert is_pdf_content(b"%PDF-1.4 rest", "text/html") is True

    def test_non_pdf_content_and_type_is_false(self):
        assert is_pdf_content(b"<html></html>", "text/html") is False

    def test_none_content_is_false(self):
        assert is_pdf_content(None, None) is False

    def test_content_shorter_than_magic_prefix_is_false(self):
        # "%PDF" is 4 bytes; the magic check requires len >= 5.
        assert is_pdf_content(b"%PDF", None) is False

    def test_empty_content_no_type_is_false(self):
        assert is_pdf_content(b"", None) is False


# --------------------------------------------------------------------------- #
# extract_pdf_text (faked pdfplumber)
# --------------------------------------------------------------------------- #
class TestExtractPdfText:
    def test_single_page_joined_returns_string(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage(text="hello")]))
        assert extract_pdf_text(b"%PDF-") == "hello"

    def test_multiple_pages_joined_with_double_newline(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage(text="p1"), FakePage(text="p2")]))
        assert extract_pdf_text(b"%PDF-") == "p1\n\np2"

    def test_join_pages_false_returns_list(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage(text="p1"), FakePage(text="p2")]))
        assert extract_pdf_text(b"%PDF-", join_pages=False) == ["p1", "p2"]

    def test_none_page_text_becomes_empty_string(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage(text=None), FakePage(text="x")]))
        assert extract_pdf_text(b"%PDF-", join_pages=False) == ["", "x"]

    def test_page_range_two_elements_is_inclusive_of_end(self, use_fake_pdf):
        pages = [FakePage(text=str(i)) for i in range(5)]
        use_fake_pdf(FakePdf(pages=pages))
        # [1, 2] -> pages at index 1 and 2 (end = 2 + 1).
        assert extract_pdf_text(b"%PDF-", page_range=[1, 2], join_pages=False) == ["1", "2"]

    def test_page_range_single_element_is_one_page(self, use_fake_pdf):
        pages = [FakePage(text=str(i)) for i in range(5)]
        use_fake_pdf(FakePdf(pages=pages))
        # [2] -> start=2, end=start+1=3 -> only page index 2.
        assert extract_pdf_text(b"%PDF-", page_range=[2], join_pages=False) == ["2"]

    def test_page_range_negative_start_clamped_to_zero(self, use_fake_pdf):
        pages = [FakePage(text=str(i)) for i in range(3)]
        use_fake_pdf(FakePdf(pages=pages))
        assert extract_pdf_text(b"%PDF-", page_range=[-10, 1], join_pages=False) == ["0", "1"]

    def test_page_range_end_clamped_to_total(self, use_fake_pdf):
        pages = [FakePage(text=str(i)) for i in range(3)]
        use_fake_pdf(FakePdf(pages=pages))
        assert extract_pdf_text(b"%PDF-", page_range=[1, 99], join_pages=False) == ["1", "2"]


# --------------------------------------------------------------------------- #
# extract_pdf_tables (faked pdfplumber)
# --------------------------------------------------------------------------- #
class TestExtractPdfTables:
    def test_basic_table_headers_rows_and_raw(self, use_fake_pdf):
        table = [["Name", "Price"], ["Widget", "9.99"]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[table])]))
        out = extract_pdf_tables(b"%PDF-")
        assert len(out) == 1
        t = out[0]
        assert t["page"] == 0
        assert t["table_index"] == 0
        assert t["headers"] == ["Name", "Price"]
        assert t["rows"] == [{"Name": "Widget", "Price": "9.99"}]
        assert t["raw"] == [["Name", "Price"], ["Widget", "9.99"]]

    def test_cells_cleaned_none_to_empty_nonstr_to_str_and_stripped(self, use_fake_pdf):
        table = [["A", "B"], ["  x  ", None], [5, True]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[table])]))
        out = extract_pdf_tables(b"%PDF-")
        rows = out[0]["rows"]
        assert rows[0] == {"A": "x", "B": ""}
        assert rows[1] == {"A": "5", "B": "True"}

    def test_header_newline_replaced_with_space_in_dict_key(self, use_fake_pdf):
        table = [["Col\nName", "B"], ["v1", "v2"]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[table])]))
        out = extract_pdf_tables(b"%PDF-")
        assert out[0]["rows"][0] == {"Col Name": "v1", "B": "v2"}

    def test_row_longer_than_headers_gets_column_index_key(self, use_fake_pdf):
        table = [["A"], ["v1", "extra"]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[table])]))
        out = extract_pdf_tables(b"%PDF-")
        assert out[0]["rows"][0] == {"A": "v1", "column_1": "extra"}

    def test_empty_header_cell_yields_column_index_key(self, use_fake_pdf):
        # A blank header cell is falsy after cleaning, so the key falls back.
        table = [["", "B"], ["v1", "v2"]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[table])]))
        out = extract_pdf_tables(b"%PDF-")
        assert out[0]["rows"][0] == {"column_0": "v1", "B": "v2"}

    def test_empty_table_is_skipped(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[[]])]))
        assert extract_pdf_tables(b"%PDF-") == []

    def test_multiple_tables_get_incrementing_table_index(self, use_fake_pdf):
        t1 = [["A"], ["1"]]
        t2 = [["B"], ["2"]]
        use_fake_pdf(FakePdf(pages=[FakePage(tables=[t1, t2])]))
        out = extract_pdf_tables(b"%PDF-")
        assert [t["table_index"] for t in out] == [0, 1]
        assert [t["headers"] for t in out] == [["A"], ["B"]]

    def test_page_range_limits_pages_scanned(self, use_fake_pdf):
        pages = [
            FakePage(tables=[[["P0"], ["a"]]]),
            FakePage(tables=[[["P1"], ["b"]]]),
            FakePage(tables=[[["P2"], ["c"]]]),
        ]
        use_fake_pdf(FakePdf(pages=pages))
        out = extract_pdf_tables(b"%PDF-", page_range=[1, 1])
        assert len(out) == 1
        assert out[0]["page"] == 1
        assert out[0]["headers"] == ["P1"]

    def test_table_settings_passed_through_when_provided(self, use_fake_pdf):
        page = FakePage(tables=[[["A"], ["1"]]])
        use_fake_pdf(FakePdf(pages=[page]))
        settings = {"vertical_strategy": "text"}
        extract_pdf_tables(b"%PDF-", table_settings=settings)
        assert page.extract_tables_calls == [settings]

    def test_no_settings_calls_extract_tables_without_settings(self, use_fake_pdf):
        page = FakePage(tables=[[["A"], ["1"]]])
        use_fake_pdf(FakePdf(pages=[page]))
        extract_pdf_tables(b"%PDF-")
        assert page.extract_tables_calls == [None]


# --------------------------------------------------------------------------- #
# extract_pdf_metadata (faked pdfplumber)
# --------------------------------------------------------------------------- #
class TestExtractPdfMetadata:
    def test_full_metadata_mapped(self, use_fake_pdf):
        meta = {
            "Title": "T",
            "Author": "A",
            "Subject": "S",
            "Creator": "C",
            "Producer": "P",
            "CreationDate": "D1",
            "ModDate": "D2",
        }
        use_fake_pdf(FakePdf(pages=[FakePage(), FakePage()], metadata=meta))
        out = extract_pdf_metadata(b"%PDF-")
        assert out == {
            "title": "T",
            "author": "A",
            "subject": "S",
            "creator": "C",
            "producer": "P",
            "creation_date": "D1",
            "modification_date": "D2",
            "page_count": 2,
        }

    def test_none_metadata_defaults_to_empty_strings(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage()], metadata=None))
        out = extract_pdf_metadata(b"%PDF-")
        assert out["title"] == ""
        assert out["author"] == ""
        assert out["page_count"] == 1

    def test_partial_metadata_fills_missing_with_empty(self, use_fake_pdf):
        use_fake_pdf(FakePdf(pages=[FakePage()], metadata={"Title": "Only Title"}))
        out = extract_pdf_metadata(b"%PDF-")
        assert out["title"] == "Only Title"
        assert out["author"] == ""
        assert out["producer"] == ""


# --------------------------------------------------------------------------- #
# process_pdf_query: dispatch (extract_pdf_* helpers patched)
# --------------------------------------------------------------------------- #
class TestProcessPdfQueryText:
    def test_text_without_expression_returns_full_text(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "full text")
        out = process_pdf_query(b"%PDF-", {"name": "f", "type": "pdf_text"})
        assert out == "full text"

    def test_text_with_regex_returns_findall_list(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "a1 b2 c3")
        out = process_pdf_query(b"%PDF-", {"type": "pdf_text", "query": r"[a-z](\d)"})
        assert out == ["1", "2", "3"]

    def test_text_regex_join_concatenates_with_pipe(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "a1 b2 c3")
        out = process_pdf_query(
            b"%PDF-", {"type": "pdf_text", "query": r"[a-z](\d)", "join": True}
        )
        assert out == "1|2|3"

    def test_text_regex_no_match_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "no digits here")
        out = process_pdf_query(b"%PDF-", {"type": "pdf_text", "query": r"(\d+)"})
        assert out == []

    def test_text_regex_no_match_with_join_stays_empty_list(self, monkeypatch):
        # `if join_flag and results:` -> an empty result set is NOT joined.
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "nope")
        out = process_pdf_query(
            b"%PDF-", {"type": "pdf_text", "query": r"(\d+)", "join": True}
        )
        assert out == []

    def test_missing_type_defaults_to_pdf_text(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_text", lambda *a, **k: "defaulted")
        out = process_pdf_query(b"%PDF-", {"name": "f"})
        assert out == "defaulted"


class TestProcessPdfQueryTable:
    def _tables(self, n):
        return [
            {"page": 0, "table_index": i, "headers": ["Name"], "rows": [{"Name": f"r{i}"}], "raw": []}
            for i in range(n)
        ]

    def test_no_tables_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: [])
        assert process_pdf_query(b"%PDF-", {"type": "pdf_table"}) == []

    def test_table_index_in_range_returns_that_table(self, monkeypatch):
        tables = self._tables(3)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "pdf_config": {"table_index": 1}})
        assert out["table_index"] == 1

    def test_single_table_no_index_returns_the_table_dict(self, monkeypatch):
        tables = self._tables(1)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table"})
        assert isinstance(out, dict)
        assert out["table_index"] == 0

    def test_multiple_tables_no_index_returns_full_list(self, monkeypatch):
        tables = self._tables(2)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table"})
        assert isinstance(out, list)
        assert len(out) == 2

    def test_out_of_range_index_with_multiple_falls_back_to_full_list(self, monkeypatch):
        tables = self._tables(2)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "pdf_config": {"table_index": 9}})
        assert isinstance(out, list)
        assert len(out) == 2

    def test_out_of_range_index_with_single_falls_back_to_first(self, monkeypatch):
        tables = self._tables(1)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "pdf_config": {"table_index": 9}})
        assert isinstance(out, dict)
        assert out["table_index"] == 0

    def test_flatten_single_table_returns_rows(self, monkeypatch):
        tables = [{"rows": [{"Name": "a"}, {"Name": "b"}], "table_index": 0}]
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "pdf_config": {"flatten": True}})
        assert out == [{"Name": "a"}, {"Name": "b"}]

    def test_flatten_multiple_tables_concatenates_rows(self, monkeypatch):
        tables = [
            {"rows": [{"n": "a"}], "table_index": 0},
            {"rows": [{"n": "b"}, {"n": "c"}], "table_index": 1},
        ]
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "pdf_config": {"flatten": True}})
        assert out == [{"n": "a"}, {"n": "b"}, {"n": "c"}]

    def test_query_expression_extracts_named_column_from_single_table(self, monkeypatch):
        tables = [{"rows": [{"Name": "x"}, {"Name": "y"}, {"Other": "z"}], "table_index": 0}]
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "query": "Name"})
        # Rows lacking the column are skipped.
        assert out == ["x", "y"]

    def test_query_expression_with_join_concatenates_column(self, monkeypatch):
        tables = [{"rows": [{"Name": "x"}, {"Name": "y"}], "table_index": 0}]
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "query": "Name", "join": True})
        assert out == "x|y"

    def test_query_expression_ignored_when_result_is_table_list(self, monkeypatch):
        # With multiple tables (a list), the column filter (`isinstance(table, dict)`)
        # is skipped and the whole list is returned.
        tables = self._tables(2)
        monkeypatch.setattr(pdf_handler, "extract_pdf_tables", lambda *a, **k: tables)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_table", "query": "Name"})
        assert isinstance(out, list)
        assert len(out) == 2


class TestProcessPdfQueryMetadataAndErrors:
    def test_metadata_delegates_to_extractor(self, monkeypatch):
        sentinel = {"title": "T", "page_count": 3}
        seen = {}

        def fake_meta(pdf_bytes):
            seen["bytes"] = pdf_bytes
            return sentinel

        monkeypatch.setattr(pdf_handler, "extract_pdf_metadata", fake_meta)
        # query / join / pdf_config are irrelevant for metadata and must be ignored.
        out = process_pdf_query(
            b"%PDF-",
            {"type": "pdf_metadata", "query": "ignored", "join": True, "pdf_config": {"page_range": [0, 1]}},
        )
        assert out == sentinel
        assert seen["bytes"] == b"%PDF-"

    def test_unknown_type_returns_none(self):
        out = process_pdf_query(b"%PDF-", {"type": "pdf_bogus"})
        assert out is None

    def test_exception_in_extraction_is_isolated_to_none(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("corrupt pdf")

        monkeypatch.setattr(pdf_handler, "extract_pdf_text", boom)
        out = process_pdf_query(b"%PDF-", {"type": "pdf_text"})
        assert out is None


# --------------------------------------------------------------------------- #
# process_pdf_queries: batch dispatch + non-PDF skipping
# --------------------------------------------------------------------------- #
class TestProcessPdfQueries:
    def test_non_pdf_type_is_skipped_as_none_without_dispatch(self, monkeypatch):
        called = []
        monkeypatch.setattr(pdf_handler, "process_pdf_query", lambda *a, **k: called.append(a) or "X")
        out = process_pdf_queries(b"%PDF-", [{"name": "t", "type": "xpath"}])
        assert out == {"t": None}
        assert called == []  # process_pdf_query never reached for a non-pdf_ type

    def test_missing_type_is_treated_as_non_pdf(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "process_pdf_query", lambda *a, **k: "X")
        out = process_pdf_queries(b"%PDF-", [{"name": "t"}])
        assert out == {"t": None}

    def test_pdf_type_is_dispatched_and_stored(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "process_pdf_query", lambda pdf_bytes, q: f"got:{q['name']}")
        out = process_pdf_queries(b"%PDF-", [{"name": "title", "type": "pdf_text"}])
        assert out == {"title": "got:title"}

    def test_missing_name_defaults_to_unnamed(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "process_pdf_query", lambda *a, **k: "v")
        out = process_pdf_queries(b"%PDF-", [{"type": "pdf_text"}])
        assert out == {"unnamed": "v"}

    def test_mixed_queries_are_independent(self, monkeypatch):
        monkeypatch.setattr(pdf_handler, "process_pdf_query", lambda pdf_bytes, q: "pdf-result")
        out = process_pdf_queries(
            b"%PDF-",
            [
                {"name": "a", "type": "pdf_text"},
                {"name": "b", "type": "regex"},
                {"name": "c", "type": "pdf_metadata"},
            ],
        )
        assert out == {"a": "pdf-result", "b": None, "c": "pdf-result"}

    def test_empty_query_list_returns_empty_dict(self):
        assert process_pdf_queries(b"%PDF-", []) == {}
