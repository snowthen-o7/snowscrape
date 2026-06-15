"""Unit tests for scraper_preview: the visual-builder selector engine.

`scraper_preview` backs the no-code Visual Scraper Builder. After a page is
fetched via the tiered scraper, three pure helpers turn a BeautifulSoup tag into
the three selector representations the UI shows for every element:

  * `generate_xpath`     -> the XPath the backend job runner will use
  * `generate_css_selector` -> the CSS selector shown in the picker
  * `generate_dom_path`  -> the human-readable "body > div.container > h1" crumb

and `test_extraction` runs a user's selector set against a freshly scraped page
so they can verify a config before saving it. None of this had dedicated
coverage, yet a silent regression here is a correctness bug the user only
discovers after a job runs and extracts nothing: a generator emitting a selector
that does not match the element it describes, or `test_extraction` mis-dispatching
a selector type / swallowing a match.

These are characterization tests (NO source change). The pure generators are
exercised against real BeautifulSoup tags. `test_extraction` calls the async
`smart_scrape` through its own private event loop, so the suite monkeypatches
`scraper_preview.smart_scrape` (the name the module bound at import) with an
async fake returning a controllable `(result, tier_used, escalation_log)` tuple;
the lxml/BeautifulSoup extraction itself runs for real.

Two quirks of `generate_xpath` are pinned deliberately as current behavior, not
endorsed as ideal: it ignores its `tree` argument entirely (selectors are built
from the tag's own id/class attributes, never by locating the node in the tree),
and when an element has multiple classes only the FIRST class reaches the
`contains(@class, ...)` predicate.
"""
import pytest
from bs4 import BeautifulSoup

import scraper_preview
from scraper_preview import (
    generate_xpath,
    generate_css_selector,
    generate_dom_path,
    # aliased: importing it under its real `test_*` name would make pytest try
    # to collect the source function itself as a test case.
    test_extraction as run_extraction,
)


def _soup(html):
    return BeautifulSoup(html, "html.parser")


def _only(html, name):
    """Return the first `name` tag parsed from `html`."""
    return _soup(html).find(name)


# ---------------------------------------------------------------------------
# generate_css_selector
# ---------------------------------------------------------------------------
class TestGenerateCssSelector:
    def test_id_yields_hash_selector(self):
        tag = _only('<div id="main">x</div>', "div")
        assert generate_css_selector(tag) == "#main"

    def test_id_wins_over_class(self):
        tag = _only('<div id="main" class="price sale">x</div>', "div")
        assert generate_css_selector(tag) == "#main"

    def test_single_class_yields_tag_dot_class(self):
        tag = _only('<div class="price">x</div>', "div")
        assert generate_css_selector(tag) == "div.price"

    def test_only_first_class_is_used(self):
        tag = _only('<div class="price sale featured">x</div>', "div")
        assert generate_css_selector(tag) == "div.price"

    def test_no_id_or_class_yields_bare_tag(self):
        tag = _only("<span>x</span>", "span")
        assert generate_css_selector(tag) == "span"

    def test_tag_name_is_preserved(self):
        tag = _only('<h1 class="title">x</h1>', "h1")
        assert generate_css_selector(tag) == "h1.title"


# ---------------------------------------------------------------------------
# generate_dom_path
# ---------------------------------------------------------------------------
class TestGenerateDomPath:
    def test_simple_nested_path_with_class_and_id(self):
        html = (
            "<html><body><div class='container'>"
            "<h1 class='title'>Hello</h1></div></body></html>"
        )
        tag = _only(html, "h1")
        # walks up to (but not including) the [document] root
        assert generate_dom_path(tag) == "html > body > div.container > h1.title"

    def test_id_used_in_path_node(self):
        html = "<html><body><section id='hero'><p>hi</p></section></body></html>"
        tag = _only(html, "p")
        assert generate_dom_path(tag) == "html > body > section#hero > p"

    def test_id_preferred_over_class_in_node(self):
        html = "<html><body><div id='wrap' class='c1 c2'><a>x</a></div></body></html>"
        tag = _only(html, "div")
        # the div node renders with its id, not its class
        assert generate_dom_path(tag) == "html > body > div#wrap"

    def test_node_without_id_or_class_is_bare_tag(self):
        html = "<html><body><ul><li>x</li></ul></body></html>"
        tag = _only(html, "li")
        assert generate_dom_path(tag) == "html > body > ul > li"

    def test_depth_capped_at_six_nearest_nodes(self):
        # 8 levels deep below the leaf's ancestry; path keeps only the 6 closest
        html = (
            "<html><body><div id='a'><div id='b'><div id='c'>"
            "<div id='d'><div id='e'><span>leaf</span>"
            "</div></div></div></div></div></body></html>"
        )
        tag = _only(html, "span")
        parts = generate_dom_path(tag).split(" > ")
        assert len(parts) == 6
        # the six nearest the leaf, top ancestors (html, body) truncated off
        assert parts == ["div#a", "div#b", "div#c", "div#d", "div#e", "span"]

    def test_document_root_not_included(self):
        tag = _only("<html><body><h2>t</h2></body></html>", "h2")
        path = generate_dom_path(tag)
        assert "[document]" not in path
        assert path.startswith("html > body")


# ---------------------------------------------------------------------------
# generate_xpath  (tree argument is intentionally ignored by the source)
# ---------------------------------------------------------------------------
class TestGenerateXpath:
    def test_id_yields_id_predicate(self):
        tag = _only('<div id="main">x</div>', "div")
        assert generate_xpath(None, tag) == "//div[@id='main']"

    def test_class_yields_contains_predicate(self):
        tag = _only('<div class="price">x</div>', "div")
        assert generate_xpath(None, tag) == "//div[contains(@class, 'price')]"

    def test_only_first_class_reaches_predicate(self):
        tag = _only('<div class="price sale featured">x</div>', "div")
        # quirk: class_str joins all classes but only class_attr[0] is emitted
        assert generate_xpath(None, tag) == "//div[contains(@class, 'price')]"

    def test_id_preferred_over_class(self):
        tag = _only('<p id="lead" class="intro">x</p>', "p")
        assert generate_xpath(None, tag) == "//p[@id='lead']"

    def test_no_id_or_class_yields_bare_tag_axis(self):
        tag = _only("<span>x</span>", "span")
        assert generate_xpath(None, tag) == "//span"

    def test_tree_argument_is_ignored(self):
        # The function never consults `tree`; an unrelated/empty tree (or None)
        # produces the identical attribute-derived XPath.
        from lxml import html as lxml_html

        tag = _only('<div class="price">x</div>', "div")
        unrelated = lxml_html.fromstring(b"<html><body><p>nothing</p></body></html>")
        assert generate_xpath(unrelated, tag) == generate_xpath(None, tag)


# ---------------------------------------------------------------------------
# test_extraction  (async smart_scrape monkeypatched)
# ---------------------------------------------------------------------------
PAGE_HTML = """
<html><head><title>Shop</title></head><body>
  <h1 class="product-name">Super Widget</h1>
  <div class="price">$42.50</div>
  <p id="desc">A great widget for testing.</p>
</body></html>
"""


def _patch_scrape(monkeypatch, result=None, tier_used=1, raises=None):
    """Replace scraper_preview.smart_scrape with an async fake.

    `result` is the scrape-result dict the source reads (.get('soup'/'html'/...)).
    If `raises` is set, the fake raises it (to exercise the fetch-failure path).
    """
    if result is None:
        result = {"html": PAGE_HTML}

    async def fake_smart_scrape(*args, **kwargs):
        if raises is not None:
            raise raises
        return result, tier_used, ["tier-1 ok"]

    monkeypatch.setattr(scraper_preview, "smart_scrape", fake_smart_scrape)


class TestTestExtraction:
    def test_returns_single_element_list_with_tier_info(self, monkeypatch):
        _patch_scrape(monkeypatch)
        out = run_extraction("https://shop.test", [])
        assert isinstance(out, list) and len(out) == 1
        info = out[0]["_tier_info"]
        assert info["tier_used"] == 1
        assert info["tier_name"] == "Lightweight"
        assert info["cost_per_page"] == 0.0001
        assert info["escalation_log"] == ["tier-1 ok"]

    def test_xpath_element_uses_text_content(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "name", "type": "xpath", "selector": "//h1"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["name"] == "Super Widget"

    def test_xpath_text_node_uses_str_branch(self, monkeypatch):
        # //title/text() returns an lxml string with no .text_content() method,
        # so the source falls through to str(elements[0]).strip()
        _patch_scrape(monkeypatch)
        sels = [{"name": "t", "type": "xpath", "selector": "//title/text()"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["t"] == "Shop"

    def test_xpath_no_match_is_none(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "missing", "type": "xpath", "selector": "//article"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["missing"] is None

    def test_css_match_uses_get_text(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "price", "type": "css", "selector": "div.price"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["price"] == "$42.50"

    def test_css_no_match_is_none(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "nope", "type": "css", "selector": ".does-not-exist"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["nope"] is None

    def test_regex_returns_first_capturing_group(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "amt", "type": "regex", "selector": r"\$(\d+\.\d{2})"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["amt"] == "42.50"

    def test_regex_without_groups_returns_full_match(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "amt", "type": "regex", "selector": r"\$\d+\.\d{2}"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["amt"] == "$42.50"

    def test_regex_no_match_is_none(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "amt", "type": "regex", "selector": r"NOTHERE(\d+)"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["amt"] is None

    def test_unknown_selector_type_is_none(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [{"name": "x", "type": "jsonpath", "selector": "$.a"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["x"] is None

    def test_invalid_xpath_is_isolated_to_none(self, monkeypatch):
        # A malformed XPath raises inside lxml; the per-selector try/except
        # must catch it and record None rather than aborting the batch.
        _patch_scrape(monkeypatch)
        sels = [{"name": "bad", "type": "xpath", "selector": "//[broken("}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["bad"] is None

    def test_multiple_selectors_are_independent(self, monkeypatch):
        _patch_scrape(monkeypatch)
        sels = [
            {"name": "name", "type": "xpath", "selector": "//h1"},
            {"name": "price", "type": "css", "selector": "div.price"},
            {"name": "amt", "type": "regex", "selector": r"\$(\d+\.\d{2})"},
            {"name": "missing", "type": "css", "selector": ".nope"},
        ]
        out = run_extraction("https://shop.test", sels)
        row = out[0]
        assert row["name"] == "Super Widget"
        assert row["price"] == "$42.50"
        assert row["amt"] == "42.50"
        assert row["missing"] is None

    def test_result_without_soup_key_parses_content(self, monkeypatch):
        # When the scrape result carries no pre-built 'soup', the source builds
        # one from the content; CSS extraction must still work.
        _patch_scrape(monkeypatch, result={"content": PAGE_HTML})
        sels = [{"name": "price", "type": "css", "selector": "div.price"}]
        out = run_extraction("https://shop.test", sels)
        assert out[0]["price"] == "$42.50"

    def test_tier_two_metadata_passes_through(self, monkeypatch):
        _patch_scrape(monkeypatch, tier_used=2)
        out = run_extraction("https://shop.test", [])
        info = out[0]["_tier_info"]
        assert info["tier_used"] == 2
        assert info["tier_name"] == "IP Rotation"
        assert info["cost_per_page"] == 0.005

    def test_unexpected_tier_raises_keyerror(self, monkeypatch):
        # Source indexes TIER_INFO[tier_used] directly (not .get), so a tier the
        # table does not define propagates a KeyError rather than degrading
        # gracefully. Pinning current behavior, not endorsing it.
        _patch_scrape(monkeypatch, tier_used=5)
        with pytest.raises(KeyError):
            run_extraction("https://shop.test", [])

    def test_scrape_failure_raises_friendly_error(self, monkeypatch):
        _patch_scrape(monkeypatch, raises=RuntimeError("all tiers blocked"))
        with pytest.raises(Exception) as exc:
            run_extraction("https://shop.test", [{"name": "n", "type": "css", "selector": "h1"}])
        assert "Failed to fetch page" in str(exc.value)
        assert "all tiers blocked" in str(exc.value)
