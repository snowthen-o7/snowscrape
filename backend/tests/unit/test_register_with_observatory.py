"""Unit tests for register_with_observatory.py (the post-deploy Observatory CLI).

`register_with_observatory.py` is the one-shot operational script Alex runs after
a deploy to register/update Snowscrape's metadata in the SnowGlobe Observatory
dashboard (via `ObservatoryClient.register`). It was the last top-level backend
module with NO dedicated coverage.

These tests do two things at once:

  1. CHARACTERIZE the script's control flow -- the `enabled` gate exits(1) when no
     SNOWGLOBE_API_KEY is set, a failed registration exits(1), a successful one
     does not, and `main()`'s argparse contract (default `dev`, the dev/prod
     choice gate, pass-through to `register_snowscrape`).

  2. PIN the registration payload as a REGRESSION guard. The script previously
     shipped stale placeholders -- `domain`/`healthEndpoint` of
     `https://api-snowscrape-{stage}.example.com` and a wrong repository URL
     `https://github.com/alexdiaz/snowscrape` -- which would have written bad
     metadata into the Observatory dashboard on the next run. The fix sources the
     real values from docs/INFRASTRUCTURE.md (prod frontend
     `https://scrape.snowforge.dev`, prod API `https://2pg2gj4048.execute-api...`,
     repo `https://github.com/snowthen-o7/snowscrape`), per stage, with
     SNOWSCRAPE_PUBLIC_URL / SNOWSCRAPE_API_BASE_URL env overrides for a
     recreated stack. The tests assert the corrected values AND explicitly assert
     the old placeholders are gone, so a regression to either placeholder fails
     loudly.

The real ObservatoryClient is replaced with a recording fake so no network is
touched and the exact `register(**kwargs)` payload is captured.
"""
import pytest

import register_with_observatory as rwo


class FakeObservatoryClient:
    """Recording stand-in for ObservatoryClient.

    Captures every `register(**kwargs)` call and returns a configurable result so
    the success / failure branches of `register_snowscrape` can be driven, and
    exposes `enabled` to drive the no-API-key gate.
    """

    def __init__(self, enabled=True, register_result=True):
        self.enabled = enabled
        self.url = 'https://snowglobe.example'
        self.site_id = 'snowscrape'
        self.register_calls = []
        self._register_result = register_result

    def register(self, **kwargs):
        self.register_calls.append(kwargs)
        return self._register_result


@pytest.fixture
def install_observatory(monkeypatch):
    """Install a FakeObservatoryClient that `register_snowscrape` will construct.

    Returns the fake instance so the test can read back the captured payload.
    """

    def _install(enabled=True, register_result=True):
        fake = FakeObservatoryClient(enabled=enabled, register_result=register_result)
        monkeypatch.setattr(rwo, 'ObservatoryClient', lambda *a, **k: fake)
        return fake

    return _install


@pytest.fixture(autouse=True)
def _clear_url_overrides(monkeypatch):
    """Default every test to the no-env-override path (stage defaults apply)."""
    monkeypatch.delenv('SNOWSCRAPE_PUBLIC_URL', raising=False)
    monkeypatch.delenv('SNOWSCRAPE_API_BASE_URL', raising=False)


# ---------------------------------------------------------------------------
# Control flow: the enabled gate and the success/failure exit contract.
# ---------------------------------------------------------------------------

def test_exits_when_observatory_disabled(install_observatory):
    """No SNOWGLOBE_API_KEY -> observatory.enabled is False -> exit(1), no register."""
    fake = install_observatory(enabled=False)
    with pytest.raises(SystemExit) as exc:
        rwo.register_snowscrape('prod')
    assert exc.value.code == 1
    assert fake.register_calls == []  # never attempts to register without a key


def test_success_does_not_exit(install_observatory):
    """A successful registration returns normally (no SystemExit)."""
    fake = install_observatory(register_result=True)
    rwo.register_snowscrape('prod')  # must not raise
    assert len(fake.register_calls) == 1


def test_exits_when_registration_fails(install_observatory):
    """register() returning falsy -> exit(1)."""
    fake = install_observatory(register_result=False)
    with pytest.raises(SystemExit) as exc:
        rwo.register_snowscrape('prod')
    assert exc.value.code == 1
    assert len(fake.register_calls) == 1  # it did attempt the registration


# ---------------------------------------------------------------------------
# Payload shape: name / type / static metadata.
# ---------------------------------------------------------------------------

def test_name_uppercases_stage_and_type_is_pipeline(install_observatory):
    fake = install_observatory()
    rwo.register_snowscrape('prod')
    payload = fake.register_calls[0]
    assert payload['name'] == 'Snowscrape (PROD)'
    assert payload['site_type'] == 'pipeline'
    assert payload['platform'] == 'AWS Lambda'


def test_static_metadata_payload(install_observatory):
    fake = install_observatory()
    rwo.register_snowscrape('dev')
    payload = fake.register_calls[0]
    assert payload['version'] == '1.0.0'
    assert payload['databases'] == [
        'DynamoDB (SnowscrapeJobs, SnowscrapeUrls, SnowscrapeSessions)'
    ]
    assert payload['services'] == [
        'S3 (snowscrape-results)',
        'SQS (SnowscrapeJobQueue)',
        'API Gateway',
        'CloudWatch',
    ]
    assert 'scraping' in payload['description'].lower()


# ---------------------------------------------------------------------------
# Regression guards: the corrected repository + domain + health endpoint, and
# explicit assertions that the old placeholders are gone.
# ---------------------------------------------------------------------------

def test_repository_is_the_real_org_repo_not_the_placeholder(install_observatory):
    fake = install_observatory()
    rwo.register_snowscrape('prod')
    repository = fake.register_calls[0]['repository']
    assert repository == 'https://github.com/snowthen-o7/snowscrape'
    # the two prior placeholder bugs must never come back
    assert 'alexdiaz' not in repository
    assert 'example.com' not in repository


def test_prod_domain_and_health_endpoint(install_observatory):
    fake = install_observatory()
    rwo.register_snowscrape('prod')
    payload = fake.register_calls[0]
    assert payload['domain'] == 'https://scrape.snowforge.dev'
    assert payload['healthEndpoint'] == (
        'https://2pg2gj4048.execute-api.us-east-2.amazonaws.com/health'
    )
    assert 'example.com' not in payload['domain']
    assert 'example.com' not in payload['healthEndpoint']


def test_dev_domain_and_health_endpoint(install_observatory):
    fake = install_observatory()
    rwo.register_snowscrape('dev')
    payload = fake.register_calls[0]
    assert payload['domain'] == 'http://localhost:3001'
    assert payload['healthEndpoint'] == (
        'https://g5vmashyda.execute-api.us-east-2.amazonaws.com/health'
    )


# ---------------------------------------------------------------------------
# Env overrides win over the stage defaults (recreated-stack safety valve).
# ---------------------------------------------------------------------------

def test_public_url_env_override_wins(install_observatory, monkeypatch):
    monkeypatch.setenv('SNOWSCRAPE_PUBLIC_URL', 'https://custom.example.org')
    fake = install_observatory()
    rwo.register_snowscrape('prod')
    assert fake.register_calls[0]['domain'] == 'https://custom.example.org'


def test_api_base_url_env_override_wins(install_observatory, monkeypatch):
    monkeypatch.setenv('SNOWSCRAPE_API_BASE_URL', 'https://newgw.execute-api.us-east-2.amazonaws.com')
    fake = install_observatory()
    rwo.register_snowscrape('prod')
    assert fake.register_calls[0]['healthEndpoint'] == (
        'https://newgw.execute-api.us-east-2.amazonaws.com/health'
    )


# ---------------------------------------------------------------------------
# The url-resolution helpers in isolation.
# ---------------------------------------------------------------------------

def test_public_url_helper_defaults_and_override(monkeypatch):
    assert rwo._public_url('prod') == 'https://scrape.snowforge.dev'
    assert rwo._public_url('dev') == 'http://localhost:3001'
    monkeypatch.setenv('SNOWSCRAPE_PUBLIC_URL', 'https://override.test')
    assert rwo._public_url('prod') == 'https://override.test'


def test_api_base_url_helper_defaults_and_override(monkeypatch):
    assert rwo._api_base_url('prod') == 'https://2pg2gj4048.execute-api.us-east-2.amazonaws.com'
    assert rwo._api_base_url('dev') == 'https://g5vmashyda.execute-api.us-east-2.amazonaws.com'
    monkeypatch.setenv('SNOWSCRAPE_API_BASE_URL', 'https://override.test')
    assert rwo._api_base_url('prod') == 'https://override.test'


def test_empty_string_env_falls_back_to_stage_default(monkeypatch):
    # An empty env var must not register a blank domain / bare /health endpoint.
    monkeypatch.setenv('SNOWSCRAPE_PUBLIC_URL', '')
    monkeypatch.setenv('SNOWSCRAPE_API_BASE_URL', '')
    assert rwo._public_url('prod') == 'https://scrape.snowforge.dev'
    assert rwo._api_base_url('prod') == 'https://2pg2gj4048.execute-api.us-east-2.amazonaws.com'


def test_api_base_url_strips_trailing_slash(monkeypatch):
    # A trailing slash on an operator-supplied base must not yield `...com//health`.
    monkeypatch.setenv('SNOWSCRAPE_API_BASE_URL', 'https://newgw.example.org/')
    assert rwo._api_base_url('prod') == 'https://newgw.example.org'


# ---------------------------------------------------------------------------
# main(): argparse default, choice gate, and pass-through.
# ---------------------------------------------------------------------------

def test_main_defaults_to_dev_stage(monkeypatch):
    seen = []
    monkeypatch.setattr(rwo, 'register_snowscrape', lambda stage: seen.append(stage))
    monkeypatch.setattr('sys.argv', ['register_with_observatory.py'])
    rwo.main()
    assert seen == ['dev']


def test_main_passes_through_prod_stage(monkeypatch):
    seen = []
    monkeypatch.setattr(rwo, 'register_snowscrape', lambda stage: seen.append(stage))
    monkeypatch.setattr('sys.argv', ['register_with_observatory.py', '--stage', 'prod'])
    rwo.main()
    assert seen == ['prod']


def test_main_rejects_invalid_stage(monkeypatch):
    # argparse exits(2) on an out-of-choice value before register_snowscrape runs.
    called = []
    monkeypatch.setattr(rwo, 'register_snowscrape', lambda stage: called.append(stage))
    monkeypatch.setattr('sys.argv', ['register_with_observatory.py', '--stage', 'staging'])
    with pytest.raises(SystemExit) as exc:
        rwo.main()
    assert exc.value.code == 2
    assert called == []
