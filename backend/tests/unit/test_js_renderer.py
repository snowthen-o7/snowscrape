"""Characterization tests for js_renderer.py (no source change).

`js_renderer` is the JavaScript-rendering tier of the live scrape engine: when a
page needs a real browser, `render_page_with_playwright` drives headless Chromium
through Playwright (launch -> context -> page -> goto -> content/screenshot) and
`render_handler` is the AWS Lambda entry point that wraps it. The whole module had
ZERO dedicated coverage, yet it is a reliability + contract boundary: the launch
flags / proxy parsing / resource-blocking / viewport options are the request
contract under load; the success/error return shapes (`status`, `content`,
`screenshot`, `error_type` 'timeout' vs 'render_error' vs 'handler_error') are a
contract the caller dispatches on; and a regression that drops `browser.close()`
or mis-maps a timeout would be invisible to a smoke test.

`playwright` is NOT a backend dependency (it ships only in a dedicated Lambda
layer), so the module cannot be imported in the unit env without a stand-in. A
minimal fake `playwright.sync_api` is injected into sys.modules BEFORE importing
js_renderer ONLY when the real package is unavailable (mirrors how the cache.py
suite injects a fake `redis`); the browser chain itself is replaced per-test by
monkeypatching `js_renderer.sync_playwright`, so no real browser ever launches.
"""

import base64
import json
import sys
import types

import pytest

# Inject a fake playwright package only if the real one is not importable, so an
# env that DOES have playwright installed still exercises the genuine import path
# (behavior is controlled per-test via monkeypatch regardless).
try:  # pragma: no cover - env-dependent
    import playwright.sync_api  # noqa: F401
except Exception:  # pragma: no cover - exercised in the backend unit env
    _fake_pw = types.ModuleType("playwright")
    _fake_sync = types.ModuleType("playwright.sync_api")

    class _FakeTimeoutError(Exception):
        pass

    def _unpatched_sync_playwright():
        raise RuntimeError("sync_playwright must be monkeypatched in tests")

    _fake_sync.sync_playwright = _unpatched_sync_playwright
    _fake_sync.TimeoutError = _FakeTimeoutError
    _fake_pw.sync_api = _fake_sync
    sys.modules["playwright"] = _fake_pw
    sys.modules["playwright.sync_api"] = _fake_sync

import js_renderer  # noqa: E402


# ---------------------------------------------------------------------------
# Fake Playwright browser chain (records calls; launches no real browser)
# ---------------------------------------------------------------------------

class FakeRoute:
    def __init__(self, resource_type):
        self.request = types.SimpleNamespace(resource_type=resource_type)
        self.aborted = False
        self.continued = False

    def abort(self):
        self.aborted = True

    def continue_(self):
        self.continued = True


class FakePage:
    def __init__(self, content="<html></html>", screenshot_bytes=b"PNGBYTES",
                 goto_exc=None, selector_exc=None):
        self._content = content
        self._screenshot_bytes = screenshot_bytes
        self._goto_exc = goto_exc
        self._selector_exc = selector_exc
        self.default_timeout = None
        self.goto_calls = []
        self.selector_calls = []
        self.screenshot_calls = []
        self.content_calls = 0

    def set_default_timeout(self, timeout):
        self.default_timeout = timeout

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        if self._goto_exc is not None:
            raise self._goto_exc

    def wait_for_selector(self, selector, timeout=None):
        self.selector_calls.append({"selector": selector, "timeout": timeout})
        if self._selector_exc is not None:
            raise self._selector_exc

    def content(self):
        self.content_calls += 1
        return self._content

    def screenshot(self, full_page=False):
        self.screenshot_calls.append({"full_page": full_page})
        return self._screenshot_bytes


class FakeContext:
    def __init__(self, page):
        self._page = page
        self.context_options = None
        self.routes = []
        self.new_page_calls = 0

    def route(self, pattern, handler):
        self.routes.append({"pattern": pattern, "handler": handler})

    def new_page(self):
        self.new_page_calls += 1
        return self._page


class FakeBrowser:
    def __init__(self, context):
        self._context = context
        self.context_options = None
        self.closed = False

    def new_context(self, **kwargs):
        self.context_options = kwargs
        self._context.context_options = kwargs
        return self._context

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self._browser = browser
        self.launch_options = None

    def launch(self, **kwargs):
        self.launch_options = kwargs
        return self._browser


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium


class FakeSyncPlaywrightCM:
    """The object sync_playwright() returns; used as `with sync_playwright()`."""

    def __init__(self, playwright):
        self._playwright = playwright
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self._playwright

    def __exit__(self, *exc):
        self.exited = True
        return False


def build_fake_playwright(content="<html></html>", screenshot_bytes=b"PNGBYTES",
                          goto_exc=None, selector_exc=None):
    """Return (factory, handle) where factory is monkeypatched onto
    js_renderer.sync_playwright and handle exposes the recorded fakes."""
    page = FakePage(content=content, screenshot_bytes=screenshot_bytes,
                    goto_exc=goto_exc, selector_exc=selector_exc)
    context = FakeContext(page)
    browser = FakeBrowser(context)
    chromium = FakeChromium(browser)
    playwright = FakePlaywright(chromium)
    cm = FakeSyncPlaywrightCM(playwright)

    def factory():
        return cm

    handle = types.SimpleNamespace(page=page, context=context, browser=browser,
                                   chromium=chromium, playwright=playwright, cm=cm)
    return factory, handle


@pytest.fixture
def fake_pw(monkeypatch):
    """Install a default fake playwright; returns the handle for assertions."""
    factory, handle = build_fake_playwright()
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    return handle


# ---------------------------------------------------------------------------
# render_page_with_playwright -- success path & return shape
# ---------------------------------------------------------------------------

def test_success_return_shape(fake_pw):
    fake_pw.page._content = "<html>hello</html>"
    result = js_renderer.render_page_with_playwright("https://ex.com", {})
    assert result == {
        "status": "success",
        "content": "<html>hello</html>",
        "screenshot": None,
        "url": "https://ex.com",
    }


def test_success_closes_browser_and_exits_context(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.browser.closed is True
    assert fake_pw.cm.entered is True
    assert fake_pw.cm.exited is True


def test_content_read_exactly_once(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.page.content_calls == 1


def test_new_page_created(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.context.new_page_calls == 1


# ---------------------------------------------------------------------------
# Launch options (the headless + hardening flag contract)
# ---------------------------------------------------------------------------

def test_launch_is_headless(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.chromium.launch_options["headless"] is True


def test_launch_args_contain_sandbox_hardening_flags(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    args = fake_pw.chromium.launch_options["args"]
    for flag in (
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
        "--single-process",
        "--disable-gpu",
    ):
        assert flag in args


def test_launch_has_no_proxy_by_default(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert "proxy" not in fake_pw.chromium.launch_options


# ---------------------------------------------------------------------------
# Defaults (empty render_config)
# ---------------------------------------------------------------------------

def test_default_wait_strategy_is_networkidle(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.page.goto_calls[0]["wait_until"] == "networkidle"


def test_default_timeout_is_30000(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.page.goto_calls[0]["timeout"] == 30000
    assert fake_pw.page.default_timeout == 30000


def test_default_viewport_1920x1080(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.context.context_options["viewport"] == {"width": 1920, "height": 1080}


def test_context_ignores_https_errors(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.context.context_options["ignore_https_errors"] is True


def test_no_user_agent_key_by_default(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert "user_agent" not in fake_pw.context.context_options


def test_no_selector_wait_by_default(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.page.selector_calls == []


def test_no_resource_route_by_default(fake_pw):
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.context.routes == []


def test_no_screenshot_by_default(fake_pw):
    result = js_renderer.render_page_with_playwright("https://ex.com", {})
    assert fake_pw.page.screenshot_calls == []
    assert result["screenshot"] is None


# ---------------------------------------------------------------------------
# Config overrides
# ---------------------------------------------------------------------------

def test_custom_wait_strategy_and_timeout(fake_pw):
    cfg = {"wait_strategy": "load", "wait_timeout_ms": 5000}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    call = fake_pw.page.goto_calls[0]
    assert call["wait_until"] == "load"
    assert call["timeout"] == 5000
    assert fake_pw.page.default_timeout == 5000


def test_custom_viewport_passed_through(fake_pw):
    cfg = {"viewport": {"width": 800, "height": 600}}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert fake_pw.context.context_options["viewport"] == {"width": 800, "height": 600}


def test_custom_user_agent_passed_through(fake_pw):
    cfg = {"user_agent": "MyAgent/1.0"}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert fake_pw.context.context_options["user_agent"] == "MyAgent/1.0"


def test_wait_for_selector_used_when_provided(fake_pw):
    cfg = {"wait_for_selector": "#ready", "wait_timeout_ms": 7000}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert fake_pw.page.selector_calls == [{"selector": "#ready", "timeout": 7000}]


# ---------------------------------------------------------------------------
# Proxy parsing
# ---------------------------------------------------------------------------

def test_proxy_url_parsed_into_launch_options(fake_pw):
    cfg = {"proxy_url": "http://user:secret@1.2.3.4:8080"}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert fake_pw.chromium.launch_options["proxy"] == {
        "server": "http://1.2.3.4:8080",
        "username": "user",
        "password": "secret",
    }


def test_proxy_url_without_port_is_ignored(fake_pw):
    # regex requires `:(\d+)` so a portless proxy does not match
    cfg = {"proxy_url": "http://user:secret@host"}
    result = js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert "proxy" not in fake_pw.chromium.launch_options
    assert result["status"] == "success"


def test_non_http_proxy_scheme_is_ignored(fake_pw):
    cfg = {"proxy_url": "socks5://1.2.3.4:9050"}
    result = js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert "proxy" not in fake_pw.chromium.launch_options
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Resource blocking (the closure registered via context.route)
# ---------------------------------------------------------------------------

def test_block_resources_registers_catch_all_route(fake_pw):
    cfg = {"block_resources": ["image", "stylesheet"]}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert len(fake_pw.context.routes) == 1
    assert fake_pw.context.routes[0]["pattern"] == "**/*"


def test_block_handler_aborts_blocked_type(fake_pw):
    cfg = {"block_resources": ["image", "stylesheet"]}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    handler = fake_pw.context.routes[0]["handler"]
    route = FakeRoute("image")
    handler(route)
    assert route.aborted is True
    assert route.continued is False


def test_block_handler_continues_unblocked_type(fake_pw):
    cfg = {"block_resources": ["image", "stylesheet"]}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    handler = fake_pw.context.routes[0]["handler"]
    route = FakeRoute("script")
    handler(route)
    assert route.continued is True
    assert route.aborted is False


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

def test_screenshot_captured_and_base64_encoded(monkeypatch):
    factory, handle = build_fake_playwright(screenshot_bytes=b"\x89PNGdata")
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    cfg = {"capture_screenshot": True}
    result = js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert result["screenshot"] == base64.b64encode(b"\x89PNGdata").decode("utf-8")
    assert handle.page.screenshot_calls == [{"full_page": False}]


def test_screenshot_full_page_flag_forwarded(monkeypatch):
    factory, handle = build_fake_playwright()
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    cfg = {"capture_screenshot": True, "screenshot_full_page": True}
    js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert handle.page.screenshot_calls == [{"full_page": True}]


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------

def test_goto_timeout_maps_to_timeout_error(monkeypatch):
    factory, handle = build_fake_playwright(
        goto_exc=js_renderer.PlaywrightTimeoutError("timed out"))
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    result = js_renderer.render_page_with_playwright("https://ex.com", {})
    assert result == {
        "status": "error",
        "error": "Timeout waiting for page to load",
        "error_type": "timeout",
        "url": "https://ex.com",
    }


def test_selector_timeout_maps_to_timeout_error(monkeypatch):
    factory, handle = build_fake_playwright(
        selector_exc=js_renderer.PlaywrightTimeoutError("selector timeout"))
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    cfg = {"wait_for_selector": "#never"}
    result = js_renderer.render_page_with_playwright("https://ex.com", cfg)
    assert result["error_type"] == "timeout"
    assert result["error"] == "Timeout waiting for page to load"


def test_generic_exception_maps_to_render_error(monkeypatch):
    factory, handle = build_fake_playwright(goto_exc=ValueError("kaboom"))
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    result = js_renderer.render_page_with_playwright("https://ex.com", {})
    assert result["status"] == "error"
    assert result["error_type"] == "render_error"
    assert result["error"] == "kaboom"
    assert result["url"] == "https://ex.com"


def test_browser_closed_when_navigation_raises(monkeypatch):
    # goto raises after the browser launches; the try/finally must still close
    # the browser so a render failure does not leak the Chromium process (#49).
    factory, handle = build_fake_playwright(goto_exc=ValueError("kaboom"))
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    js_renderer.render_page_with_playwright("https://ex.com", {})
    assert handle.browser.closed is True
    assert handle.cm.exited is True


def test_browser_closed_when_selector_wait_raises(monkeypatch):
    # An exception AFTER a successful goto (during wait_for_selector) must also
    # close the browser via the finally, not just the navigation-failure path.
    factory, handle = build_fake_playwright(
        selector_exc=js_renderer.PlaywrightTimeoutError("selector timeout"))
    monkeypatch.setattr(js_renderer, "sync_playwright", factory)
    js_renderer.render_page_with_playwright("https://ex.com", {"wait_for_selector": "#never"})
    assert handle.browser.closed is True
    assert handle.cm.exited is True


# ---------------------------------------------------------------------------
# render_handler (Lambda entry point)
# ---------------------------------------------------------------------------

def test_handler_missing_url_returns_400_without_rendering(monkeypatch):
    calls = []
    monkeypatch.setattr(js_renderer, "render_page_with_playwright",
                        lambda *a, **k: calls.append((a, k)))
    resp = js_renderer.render_handler({}, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body == {"status": "error", "error": "URL is required"}
    assert calls == []  # render must not run when url is missing


def test_handler_success_returns_200_with_result_body(monkeypatch):
    result = {"status": "success", "content": "<html/>", "screenshot": None, "url": "u"}
    monkeypatch.setattr(js_renderer, "render_page_with_playwright",
                        lambda url, cfg: result)
    resp = js_renderer.render_handler({"url": "https://ex.com"}, None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == result


def test_handler_render_error_returns_500_with_result_body(monkeypatch):
    result = {"status": "error", "error": "boom", "error_type": "render_error", "url": "u"}
    monkeypatch.setattr(js_renderer, "render_page_with_playwright",
                        lambda url, cfg: result)
    resp = js_renderer.render_handler({"url": "https://ex.com"}, None)
    assert resp["statusCode"] == 500
    assert json.loads(resp["body"]) == result


def test_handler_forwards_url_and_render_config(monkeypatch):
    captured = {}

    def spy(url, cfg):
        captured["url"] = url
        captured["cfg"] = cfg
        return {"status": "success"}

    monkeypatch.setattr(js_renderer, "render_page_with_playwright", spy)
    cfg = {"wait_strategy": "load", "capture_screenshot": True}
    js_renderer.render_handler({"url": "https://ex.com", "render_config": cfg}, None)
    assert captured["url"] == "https://ex.com"
    assert captured["cfg"] == cfg


def test_handler_defaults_render_config_to_empty_dict(monkeypatch):
    captured = {}

    def spy(url, cfg):
        captured["cfg"] = cfg
        return {"status": "success"}

    monkeypatch.setattr(js_renderer, "render_page_with_playwright", spy)
    js_renderer.render_handler({"url": "https://ex.com"}, None)
    assert captured["cfg"] == {}


def test_handler_top_level_exception_returns_500_handler_error():
    # event=None -> event.get(...) raises AttributeError, caught by the outer try
    resp = js_renderer.render_handler(None, None)
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert body["status"] == "error"
    assert body["error_type"] == "handler_error"
