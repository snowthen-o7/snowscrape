"""Guards that openapi.yml stays consistent with the real auth model.

The canonical source of truth for "which endpoints accept a programmatic API key"
is `resolve_user_id` in utils.py: every handler that calls it accepts either a
Clerk JWT or an `sk_live_...` API key. Those are exactly the `/jobs` data-plane
operations. Control-plane endpoints validate Clerk JWTs directly and must NOT
advertise the API-key scheme. These tests pin the spec to that contract so the
docs cannot silently drift away from the implementation again.
"""

from pathlib import Path

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
    """The set of security scheme names accepted by an operation."""
    schemes = set()
    for requirement in operation.get("security", []):
        schemes.update(requirement.keys())
    return schemes


def test_spec_parses(spec):
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec and spec["paths"]


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
def test_control_plane_rejects_api_key(operations, operation_id):
    assert operation_id in operations, f"missing operation {operation_id} in spec"
    schemes = _schemes_for(operations[operation_id])
    assert API_KEY_SCHEME not in schemes, (
        f"{operation_id} is control-plane and must stay Clerk-only (no ApiKeyAuth)"
    )
