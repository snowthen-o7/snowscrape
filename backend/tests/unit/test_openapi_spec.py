"""Guards that openapi.yml stays consistent with the real auth model.

The canonical source of truth for "which endpoints accept a programmatic API key"
is `resolve_user_id` in utils.py: every handler that calls it accepts either a
Clerk JWT or an `sk_live_...` API key. Those are exactly the `/jobs` data-plane
operations. Control-plane endpoints validate Clerk JWTs directly and must NOT
advertise the API-key scheme. These tests pin the spec to that contract so the
docs cannot silently drift away from the implementation again.
"""

from pathlib import Path
from urllib.parse import urlsplit

import pytest

yaml = pytest.importorskip("yaml")

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.yml"

# operationIds whose handlers call resolve_user_id (the /jobs data-plane).
# Keep in sync with the resolve_user_id call sites in handler.py.
DATA_PLANE_OPERATIONS = {
    "createJob",
    "getAllJobStatuses",
    "getJobDetails",
    "updateJob",
    "deleteJob",
    "pauseJob",
    "resumeJob",
    "cancelJob",
    "refreshJob",
    "getJobCrawls",
    "getCrawlDetails",
    "downloadResults",
    "previewResults",
}

# Representative control-plane operations that must stay Clerk-only.
CLERK_ONLY_OPERATIONS = {
    "createApiKey",
    "listApiKeys",
    "revokeApiKey",
    "createTemplate",
    "listTemplates",
    "createWebhook",
    "createCheckoutSession",
    "getSubscription",
}

API_KEY_SCHEME = "ApiKeyAuth"
CLERK_SCHEME = "BearerAuth"

# The live, publicly reachable production API Gateway (HTTP API V2, us-east-2).
# It runs on the auto `$default` stage, so routes are served at the host root
# with no stage path prefix. Source of truth: docs/INFRASTRUCTURE.md and
# frontend/.env.example NEXT_PUBLIC_API_BASE_URL (the working client).
PROD_GATEWAY_URL = "https://2pg2gj4048.execute-api.us-east-2.amazonaws.com"


@pytest.fixture(scope="module")
def spec():
    with OPENAPI_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def operations(spec):
    """Map operationId -> the operation object across every path/method."""
    ops = {}
    for path_item in spec["paths"].values():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                ops[operation["operationId"]] = operation
    return ops


def _schemes_for(operation):
    """The set of security scheme names declared on an operation itself."""
    schemes = set()
    for requirement in operation.get("security", []):
        schemes.update(requirement.keys())
    return schemes


def _effective_schemes(operation, global_security):
    """The set of accepted schemes, falling back to the global default.

    OpenAPI: an operation with no `security` key inherits the document-level
    default. Use this so the control-plane guard also catches a regression where
    an op's entire `security` block is deleted (which would otherwise read as
    "no auth" instead of inheriting the Clerk-only default).
    """
    if "security" not in operation:
        schemes = set()
        for requirement in global_security:
            schemes.update(requirement.keys())
        return schemes
    return _schemes_for(operation)


def test_spec_parses(spec):
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec and spec["paths"]


def _resolved_server_urls(spec):
    """Each server URL with its variable defaults substituted in.

    SDK generators and Swagger UI's "Try it out" resolve a server by filling
    every templated variable with its `default`, so a default of `REPLACE_ME`
    (or a localhost entry) yields a URL that points nowhere usable.
    """
    urls = []
    for server in spec.get("servers", []):
        url = server["url"]
        for name, var in (server.get("variables") or {}).items():
            url = url.replace("{" + name + "}", str(var.get("default", "")))
        urls.append(url)
    return urls


def test_servers_have_no_placeholder(spec):
    """No server URL or variable default may ship a placeholder value."""
    for server in spec.get("servers", []):
        assert "REPLACE_ME" not in server["url"], (
            f"server url still has a placeholder: {server['url']}"
        )
        for name, var in (server.get("variables") or {}).items():
            assert "REPLACE_ME" not in str(var.get("default", "")), (
                f"server variable {name!r} default must be a real value, "
                "not a placeholder"
            )


def test_servers_resolve_to_real_gateways(spec):
    """The spec must point clients at the real prod gateway, and not at a
    misleading localhost host (the backend is only reachable via API Gateway)."""
    urls = _resolved_server_urls(spec)
    assert PROD_GATEWAY_URL in urls, (
        f"servers must include the real prod gateway {PROD_GATEWAY_URL}; got {urls}"
    )
    assert not any("localhost" in u for u in urls), (
        f"drop the misleading localhost server entry; got {urls}"
    )


def test_servers_have_no_stage_path_prefix(spec):
    """These are HTTP API V2 gateways on the `$default` stage: routes are served
    at the host root, so a server URL must not carry a stage path segment such as
    `/prod` or `/dev` (that would make every "Try it out" resolve to a dead path)."""
    for url in _resolved_server_urls(spec):
        path = urlsplit(url).path.rstrip("/")
        assert path == "", (
            f"server url {url!r} has a path segment {path!r}; HTTP API V2 routes "
            "are served at the host root, so the server must be the bare host"
        )


def test_api_key_scheme_is_defined(spec):
    schemes = spec["components"]["securitySchemes"]
    assert API_KEY_SCHEME in schemes, "ApiKeyAuth security scheme must be defined"
    api_key = schemes[API_KEY_SCHEME]
    assert api_key["type"] == "http"
    assert api_key["scheme"] == "bearer"


@pytest.mark.parametrize("operation_id", sorted(DATA_PLANE_OPERATIONS))
def test_data_plane_accepts_api_key(operations, operation_id):
    assert operation_id in operations, f"missing operation {operation_id} in spec"
    schemes = _schemes_for(operations[operation_id])
    assert API_KEY_SCHEME in schemes, (
        f"{operation_id} is a /jobs data-plane op and must accept ApiKeyAuth"
    )
    assert CLERK_SCHEME in schemes, (
        f"{operation_id} must still accept the Clerk JWT (BearerAuth)"
    )


@pytest.mark.parametrize("operation_id", sorted(CLERK_ONLY_OPERATIONS))
def test_control_plane_is_clerk_only(operations, spec, operation_id):
    assert operation_id in operations, f"missing operation {operation_id} in spec"
    schemes = _effective_schemes(operations[operation_id], spec.get("security", []))
    # Control-plane must resolve to Clerk-only: BearerAuth present, ApiKeyAuth absent.
    # Using effective schemes also catches a deleted security block (which would
    # leave the op unauthenticated rather than Clerk-gated).
    assert schemes == {CLERK_SCHEME}, (
        f"{operation_id} is control-plane and must stay Clerk-only "
        f"(effective schemes were {schemes or 'none'})"
    )
