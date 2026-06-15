"""Unit tests for scraper_preview_async: the WebSocket-streamed async preview.

The synchronous `scraper_preview.test_extraction` path runs inside the 30s API
Gateway window. For pages that need a slower tier (proxy / Firecrawl), the
preview is run out-of-band instead: `start_async_scrape` returns a `task_id`
immediately and fires a worker Lambda (`invoke_scraper_async`), and the worker
(`scrape_with_websocket_updates`) does the real scrape while pushing progress to
the browser over the WebSocket fan-out (`broadcast_to_user`). None of this had
dedicated coverage, yet it is a reliability + contract boundary on three fronts:

  * a regression that drops the worker invoke leaves the user's preview hanging
    forever with a `task_id` that never resolves;
  * the missing-`ASYNC_WORKER_FUNCTION_NAME` guard must raise rather than
    silently no-op (an unconfigured stage would otherwise look "started" but
    never scrape);
  * the WebSocket message shapes (`scraper:progress` / `scraper:complete` /
    `scraper:error`) and the `start` payload (`task_id`, `websocket_channel`,
    `websocket_url`) are a contract the frontend consumes; a drifted field name
    or status string silently breaks the live progress UI.

Characterization only: NO source change. The async `smart_scrape` is replaced by
an async fake returning a controllable `(result, tier_used, escalation_log)`
tuple (the lxml/BeautifulSoup element extraction then runs for real against the
fake's HTML); `broadcast_to_user` is replaced by a recorder so the exact emitted
messages are asserted without a real API Gateway; and `lambda_client` is a Mock
so the async self-invoke is asserted without AWS. One behavioral contrast is
pinned deliberately: unlike the synchronous `test_extraction` (which RAISES on a
scrape/tier failure), the worker SWALLOWS every exception and, when a WebSocket
domain is configured, surfaces it as a single `scraper:error` message.
"""
import json
import os
from unittest.mock import Mock

import pytest

# scraper_preview_async builds a module-level boto3 Lambda client at import and
# imports websocket_handler / tiered_scraper; ensure a region + creds exist so
# the import succeeds even on a bare box. setdefault never clobbers real values.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-2')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')

import scraper_preview_async


PAGE_HTML = """
<html><head><title>Shop</title></head><body>
  <h1 class="product-name">Super Widget</h1>
  <div class="price">$42.50</div>
  <p id="desc">A great widget for testing.</p>
</body></html>
"""


# ─── helpers / fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def ws_recorder(monkeypatch):
    """Replace broadcast_to_user with a recorder of every (domain, stage, user, msg)."""
    calls = []

    def fake_broadcast(domain, stage, user_id, message):
        calls.append({
            'domain': domain,
            'stage': stage,
            'user_id': user_id,
            'message': message,
        })

    monkeypatch.setattr(scraper_preview_async, 'broadcast_to_user', fake_broadcast)
    return calls


def _patch_scrape(monkeypatch, result=None, tier_used=1, escalation_log=None, raises=None):
    """Replace scraper_preview_async.smart_scrape with an async fake."""
    if result is None:
        result = {'html': PAGE_HTML}
    if escalation_log is None:
        escalation_log = ['tier-1 ok']

    async def fake_smart_scrape(*args, **kwargs):
        if raises is not None:
            raise raises
        return result, tier_used, escalation_log

    monkeypatch.setattr(scraper_preview_async, 'smart_scrape', fake_smart_scrape)


def _messages(calls):
    return [c['message'] for c in calls]


def _by_status(calls, status):
    return [c['message'] for c in calls if c['message'].get('status') == status]


def _complete_data(calls):
    done = _by_status(calls, 'completed')
    assert len(done) == 1, f"expected exactly one completion, got {len(done)}"
    return done[0]['data']


# ═══════════════════════════════════════════════════════════════════════════════
# invoke_scraper_async  (async Lambda self-invoke)
# ═══════════════════════════════════════════════════════════════════════════════
class TestInvokeScraperAsync:
    def test_missing_function_name_raises_and_never_invokes(self, monkeypatch):
        monkeypatch.delenv('ASYNC_WORKER_FUNCTION_NAME', raising=False)
        fake = Mock()
        monkeypatch.setattr(scraper_preview_async, 'lambda_client', fake)
        with pytest.raises(RuntimeError) as exc:
            scraper_preview_async.invoke_scraper_async('u1', 'https://x.test', 'task-1')
        assert 'ASYNC_WORKER_FUNCTION_NAME' in str(exc.value)
        fake.invoke.assert_not_called()

    def test_invokes_worker_with_event_type_and_exact_payload(self, monkeypatch):
        monkeypatch.setenv('ASYNC_WORKER_FUNCTION_NAME', 'snowscrape-worker')
        fake = Mock()
        fake.invoke.return_value = {'StatusCode': 202}
        monkeypatch.setattr(scraper_preview_async, 'lambda_client', fake)

        scraper_preview_async.invoke_scraper_async(
            'u1', 'https://x.test', 'task-1', min_tier=2, max_tier=4
        )

        assert fake.invoke.call_count == 1
        kwargs = fake.invoke.call_args.kwargs
        assert kwargs['FunctionName'] == 'snowscrape-worker'
        assert kwargs['InvocationType'] == 'Event'  # async, fire-and-forget
        payload = json.loads(kwargs['Payload'])
        assert payload == {
            'task_id': 'task-1',
            'user_id': 'u1',
            'url': 'https://x.test',
            'min_tier': 2,
            'max_tier': 4,
            'source': 'async_scraper',
        }

    def test_default_tiers_in_payload(self, monkeypatch):
        monkeypatch.setenv('ASYNC_WORKER_FUNCTION_NAME', 'snowscrape-worker')
        fake = Mock()
        fake.invoke.return_value = {'StatusCode': 202}
        monkeypatch.setattr(scraper_preview_async, 'lambda_client', fake)

        scraper_preview_async.invoke_scraper_async('u1', 'https://x.test', 'task-1')

        payload = json.loads(fake.invoke.call_args.kwargs['Payload'])
        assert payload['min_tier'] == 1
        assert payload['max_tier'] == 4

    def test_invoke_failure_propagates(self, monkeypatch):
        monkeypatch.setenv('ASYNC_WORKER_FUNCTION_NAME', 'snowscrape-worker')
        fake = Mock()
        fake.invoke.side_effect = RuntimeError('lambda down')
        monkeypatch.setattr(scraper_preview_async, 'lambda_client', fake)
        with pytest.raises(RuntimeError, match='lambda down'):
            scraper_preview_async.invoke_scraper_async('u1', 'https://x.test', 'task-1')


# ═══════════════════════════════════════════════════════════════════════════════
# start_async_scrape  (returns immediately, fires the worker)
# ═══════════════════════════════════════════════════════════════════════════════
class TestStartAsyncScrape:
    @pytest.fixture
    def invoke_recorder(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            scraper_preview_async, 'invoke_scraper_async',
            lambda **kwargs: calls.append(kwargs),
        )
        return calls

    def test_returns_started_payload_and_fires_worker(self, monkeypatch, invoke_recorder):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.setenv('WS_API_STAGE', 'prod')

        out = scraper_preview_async.start_async_scrape('u1', 'https://x.test', min_tier=1, max_tier=3)

        assert out['status'] == 'started'
        assert out['url'] == 'https://x.test'
        task_id = out['task_id']
        assert isinstance(task_id, str) and task_id
        # the worker was invoked exactly once, for the SAME task_id it returned
        assert len(invoke_recorder) == 1
        fired = invoke_recorder[0]
        assert fired['task_id'] == task_id
        assert fired['user_id'] == 'u1'
        assert fired['url'] == 'https://x.test'
        assert fired['min_tier'] == 1 and fired['max_tier'] == 3

    def test_websocket_channel_and_url_shape(self, monkeypatch, invoke_recorder):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.setenv('WS_API_STAGE', 'prod')

        out = scraper_preview_async.start_async_scrape('u1', 'https://x.test')

        assert out['websocket_channel'] == f"scraper:{out['task_id']}"
        assert out['websocket_url'] == 'wss://ws.example.com/prod'

    def test_websocket_url_defaults_stage_to_dev(self, monkeypatch, invoke_recorder):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.delenv('WS_API_STAGE', raising=False)

        out = scraper_preview_async.start_async_scrape('u1', 'https://x.test')

        assert out['websocket_url'] == 'wss://ws.example.com/dev'

    def test_each_call_gets_a_distinct_task_id(self, monkeypatch, invoke_recorder):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        a = scraper_preview_async.start_async_scrape('u1', 'https://x.test')
        b = scraper_preview_async.start_async_scrape('u1', 'https://x.test')
        assert a['task_id'] != b['task_id']

    def test_worker_invoke_failure_propagates(self, monkeypatch):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')

        def boom(**kwargs):
            raise RuntimeError('invoke failed')

        monkeypatch.setattr(scraper_preview_async, 'invoke_scraper_async', boom)
        with pytest.raises(RuntimeError, match='invoke failed'):
            scraper_preview_async.start_async_scrape('u1', 'https://x.test')


# ═══════════════════════════════════════════════════════════════════════════════
# scrape_with_websocket_updates  (the worker: scrape + WS progress fan-out)
# ═══════════════════════════════════════════════════════════════════════════════
class TestWorkerNoWebSocketDomain:
    def test_no_domain_emits_nothing_and_does_not_raise(self, monkeypatch, ws_recorder):
        monkeypatch.delenv('WS_API_DOMAIN', raising=False)
        _patch_scrape(monkeypatch)
        # must complete cleanly even with no WebSocket configured
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert ws_recorder == []

    def test_no_domain_swallows_scrape_failure_silently(self, monkeypatch, ws_recorder):
        monkeypatch.delenv('WS_API_DOMAIN', raising=False)
        _patch_scrape(monkeypatch, raises=RuntimeError('all tiers blocked'))
        # no exception escapes, and with no domain there is nothing to broadcast
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert ws_recorder == []


class TestWorkerHappyPath:
    @pytest.fixture(autouse=True)
    def _domain(self, monkeypatch):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.setenv('WS_API_STAGE', 'prod')

    def test_first_message_is_starting_progress(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        first = ws_recorder[0]
        assert first['domain'] == 'ws.example.com'
        assert first['stage'] == 'prod'
        assert first['user_id'] == 'u1'
        msg = first['message']
        assert msg['type'] == 'scraper:progress'
        assert msg['status'] == 'starting'
        assert msg['task_id'] == 't1'
        assert msg['tier'] == 1
        assert 'https://x.test' in msg['message']

    def test_last_message_is_completion_with_data(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        last = ws_recorder[-1]['message']
        assert last['type'] == 'scraper:complete'
        assert last['status'] == 'completed'
        assert last['task_id'] == 't1'
        data = last['data']
        assert data['url'] == 'https://x.test'
        assert data['title'] == 'Shop'
        assert isinstance(data['elements'], list) and data['elements']

    def test_tier_one_emits_only_starting_then_complete(self, monkeypatch, ws_recorder):
        # tier_used == min_tier, so no escalation message in between
        _patch_scrape(monkeypatch, tier_used=1)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        statuses = [m['status'] for m in _messages(ws_recorder)]
        assert statuses == ['starting', 'completed']

    def test_completion_tier_info_for_tier_one(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, tier_used=1, escalation_log=['ok'])
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        info = _complete_data(ws_recorder)['tier_info']
        assert info['tier_used'] == 1
        assert info['tier_name'] == 'Lightweight'
        assert info['cost_per_page'] == 0.0001
        assert info['escalation_log'] == ['ok']

    def test_elements_carry_generated_selectors(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        elements = _complete_data(ws_recorder)['elements']
        by_text = {e['text']: e for e in elements}
        assert 'Super Widget' in by_text
        h1 = by_text['Super Widget']
        assert h1['type'] == 'h1'
        assert h1['css'] == 'h1.product-name'
        assert h1['xpath'] == "//h1[contains(@class, 'product-name')]"
        assert h1['id'].startswith('el-')
        # the id-bearing paragraph extracts via its id
        assert 'A great widget for testing.' in by_text
        p = by_text['A great widget for testing.']
        assert p['type'] == 'p'
        assert p['css'] == '#desc'

    def test_markdown_passed_through_when_present(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, result={'html': PAGE_HTML, 'markdown': '# Shop'})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert _complete_data(ws_recorder)['markdown'] == '# Shop'

    def test_no_markdown_key_when_absent(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, result={'html': PAGE_HTML})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert 'markdown' not in _complete_data(ws_recorder)

    def test_content_key_used_when_no_soup_or_html(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, result={'content': PAGE_HTML})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        data = _complete_data(ws_recorder)
        assert data['title'] == 'Shop'
        assert any(e['text'] == '$42.50' for e in data['elements'])

    def test_title_falls_back_to_url_without_title_tag(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, result={'html': '<html><body><h1>Only heading</h1></body></html>'})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert _complete_data(ws_recorder)['title'] == 'https://x.test'


class TestWorkerEscalation:
    @pytest.fixture(autouse=True)
    def _domain(self, monkeypatch):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.setenv('WS_API_STAGE', 'prod')

    def test_escalation_message_emitted_when_tier_climbs(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, tier_used=2, escalation_log=['t1->t2'])
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        esc = _by_status(ws_recorder, 'escalated')
        assert len(esc) == 1
        m = esc[0]
        assert m['type'] == 'scraper:progress'
        assert m['tier'] == 2
        assert m['tier_name'] == 'IP Rotation'
        assert m['cost_per_page'] == 0.005
        assert m['escalation_log'] == ['t1->t2']
        assert 'Tier 2' in m['message'] and 'IP Rotation' in m['message']

    def test_message_order_is_starting_escalated_completed(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, tier_used=2)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        statuses = [m['status'] for m in _messages(ws_recorder)]
        assert statuses == ['starting', 'escalated', 'completed']

    def test_no_escalation_message_when_tier_equals_min(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, tier_used=3)
        # min_tier == tier_used == 3: the `tier_used > min_tier` guard is false
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=3)
        assert _by_status(ws_recorder, 'escalated') == []

    def test_completion_tier_info_reflects_escalated_tier(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, tier_used=4)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        info = _complete_data(ws_recorder)['tier_info']
        assert info['tier_used'] == 4
        assert info['tier_name'] == 'Firecrawl Anti-Bot'
        assert info['cost_per_page'] == 0.05


class TestWorkerElementFiltering:
    @pytest.fixture(autouse=True)
    def _domain(self, monkeypatch):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')

    def test_short_and_blank_text_elements_skipped(self, monkeypatch, ws_recorder):
        html = (
            '<html><body>'
            '<p>x</p>'          # len 1 -> skipped (< 2)
            '<p>   </p>'        # whitespace only -> stripped to '' -> skipped
            '<p>keep this</p>'  # kept
            '</body></html>'
        )
        _patch_scrape(monkeypatch, result={'html': html})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        texts = [e['text'] for e in _complete_data(ws_recorder)['elements']]
        assert 'keep this' in texts
        assert 'x' not in texts
        assert all(t.strip() for t in texts)

    def test_long_text_is_truncated_to_300_plus_ellipsis(self, monkeypatch, ws_recorder):
        long_text = 'A' * 400
        _patch_scrape(monkeypatch, result={'html': f'<html><body><p>{long_text}</p></body></html>'})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        el = _complete_data(ws_recorder)['elements'][0]
        assert el['text'] == 'A' * 300 + '...'
        assert len(el['text']) == 303

    def test_element_count_capped_at_100(self, monkeypatch, ws_recorder):
        paras = ''.join(f'<p>paragraph number {i}</p>' for i in range(120))
        _patch_scrape(monkeypatch, result={'html': f'<html><body>{paras}</body></html>'})
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        assert len(_complete_data(ws_recorder)['elements']) == 100


class TestWorkerErrorPath:
    @pytest.fixture(autouse=True)
    def _domain(self, monkeypatch):
        monkeypatch.setenv('WS_API_DOMAIN', 'ws.example.com')
        monkeypatch.setenv('WS_API_STAGE', 'prod')

    def test_scrape_failure_emits_error_message_not_raise(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, raises=RuntimeError('all tiers blocked'))
        # the worker swallows the exception (contrast with sync test_extraction)
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        errs = _by_status(ws_recorder, 'failed')
        assert len(errs) == 1
        m = errs[0]
        assert m['type'] == 'scraper:error'
        assert m['task_id'] == 't1'
        assert 'all tiers blocked' in m['error']
        # no completion was emitted
        assert _by_status(ws_recorder, 'completed') == []

    def test_starting_message_precedes_error(self, monkeypatch, ws_recorder):
        _patch_scrape(monkeypatch, raises=RuntimeError('boom'))
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test')
        statuses = [m['status'] for m in _messages(ws_recorder)]
        assert statuses == ['starting', 'failed']

    def test_unexpected_tier_is_swallowed_as_error(self, monkeypatch, ws_recorder):
        # The source indexes TIER_INFO[tier_used] directly; an undefined tier
        # raises KeyError, which the worker's broad except turns into a single
        # scraper:error message (it does NOT propagate, unlike test_extraction).
        _patch_scrape(monkeypatch, tier_used=9, escalation_log=['weird'])
        scraper_preview_async.scrape_with_websocket_updates('t1', 'u1', 'https://x.test', min_tier=1)
        assert len(_by_status(ws_recorder, 'failed')) == 1
        assert _by_status(ws_recorder, 'completed') == []
