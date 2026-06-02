# Google Docs Destination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let SnowScrape users connect a Google account once, define reusable "export destinations," and have job results automatically delivered to Google Docs in their Drive after each job run.

**Architecture:** Mirror the existing webhook delivery pipeline (DynamoDB → SQS → Lambda). Add three new tables (`GoogleAccounts`, `ExportDestinations`, `DocsExports`), a new SQS queue (`DocsExportQueue` + DLQ), and a new SQS-triggered Lambda (`docs_export_handler`). OAuth refresh tokens are KMS-encrypted at rest. On job completion, `DocsExporter` fans out one SQS message per destination, just like `WebhookDispatcher` already does. Per-user only (no org sharing in v1). OAuth scopes: `drive.file` + `drive.metadata.readonly` so users can pick existing Drive folders. Export usage is not metered against plan limits in v1.

**Tech Stack:** Python 3.12 Lambda, DynamoDB, SQS, KMS, SST Ion (TypeScript IaC), `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, Next.js App Router, Clerk auth, React Hook Form + Zod, TanStack Query, Radix UI.

---

## File Structure

### Backend — new files
- `backend/google_oauth.py` — OAuth flow helpers (consent URL, code→token exchange, token refresh, KMS encrypt/decrypt)
- `backend/google_account_handler.py` — HTTP handlers for `/integrations/google/*` (auth URL, callback, list, revoke)
- `backend/export_destination_handler.py` — HTTP handlers for `/export-destinations` (CRUD)
- `backend/docs_exporter.py` — `DocsExporter` class that dispatches export messages to SQS (mirrors `webhook_dispatcher.py`)
- `backend/docs_export_handler.py` — SQS-triggered Lambda that writes to Google Docs
- `backend/docs_formatter.py` — Pure function: scrape rows → Google Docs `batchUpdate` request list
- `backend/tests/unit/test_google_oauth.py`
- `backend/tests/unit/test_docs_formatter.py`
- `backend/tests/unit/test_export_destination_handler.py`
- `backend/tests/unit/test_google_account_handler.py`
- `backend/tests/unit/test_docs_exporter.py`
- `backend/tests/integration/test_docs_export_flow.py`

### Backend — modified files
- `backend/pyproject.toml` — add Google API dependencies
- `backend/job_manager.py` — fan out to `DocsExporter` alongside existing `WebhookDispatcher.dispatch_job_completed` calls (around line 533)

### Infrastructure — modified files
- `sst.config.ts` — add KMS key, 3 DynamoDB tables, SQS queue+DLQ, SQS subscriber Lambda, 8 HTTP routes, env vars, IAM permissions

### Frontend — new files
- `frontend/lib/api/integrations.ts` — typed API client functions
- `frontend/lib/api/destinations.ts` — typed API client functions
- `frontend/lib/hooks/useGoogleAccount.ts` — TanStack Query hooks
- `frontend/lib/hooks/useDestinations.ts` — TanStack Query hooks
- `frontend/app/(application)/dashboard/integrations/page.tsx` — Connect/disconnect Google account
- `frontend/app/(application)/dashboard/integrations/google/callback/page.tsx` — OAuth redirect landing page
- `frontend/app/(application)/dashboard/destinations/page.tsx` — Destination list
- `frontend/app/(application)/dashboard/destinations/new/page.tsx` — Create destination form
- `frontend/components/destinations/DrivePicker.tsx` — Google Drive folder picker (uses `gapi.picker`)
- `frontend/components/destinations/DestinationSelector.tsx` — Multi-select used in job creation
- `frontend/e2e/google-docs-destination.spec.ts` — Playwright e2e covering the connect → create destination → run job → doc appears flow (uses mocked Google API)

### Frontend — modified files
- `frontend/app/(application)/dashboard/jobs/new/page.tsx` — add "Send results to" section using `DestinationSelector`
- `frontend/components/layout/AppSidebar.tsx` — add "Integrations" and "Destinations" nav entries
- `frontend/next.config.mjs` — allowlist `apis.google.com` for the Picker SDK script

---

## Phase 1: Infrastructure & Data Model

### Task 1: Add Google API Python dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add dependencies**

In `backend/pyproject.toml`, locate the `[project] dependencies = [...]` array and add three entries (preserving existing ones):

```toml
"google-auth>=2.35.0",
"google-auth-oauthlib>=1.2.1",
"google-api-python-client>=2.150.0",
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`
Expected: Resolves and installs the three packages; no errors.

- [ ] **Step 3: Verify importable**

Run: `uv run python -c "from google_auth_oauthlib.flow import Flow; from googleapiclient.discovery import build; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml uv.lock
git commit -m "feat(backend): add Google API dependencies for Docs export"
```

---

### Task 2: Provision KMS key, DynamoDB tables, SQS queue in SST

**Files:**
- Modify: `sst.config.ts`

- [ ] **Step 1: Add KMS key declaration**

After the `subscriptionsTable` block (~line 190), insert:

```ts
    // ─── KMS Key for OAuth Token Encryption ───────────────────────────

    const oauthTokenKey = new aws.kms.Key("OAuthTokenKey", {
      description: `SnowScrape OAuth refresh token encryption (${stage})`,
      enableKeyRotation: true,
      deletionWindowInDays: 30,
    });

    new aws.kms.Alias("OAuthTokenKeyAlias", {
      name: `alias/snowscrape-${stage}-oauth-tokens`,
      targetKeyId: oauthTokenKey.keyId,
    });
```

- [ ] **Step 2: Add three new DynamoDB tables**

After the `apiKeysTable` block (~line 210), insert:

```ts
    const googleAccountsTable = new sst.aws.Dynamo("GoogleAccounts", {
      fields: {
        user_id: "string",
        google_user_id: "string",
      },
      primaryIndex: { hashKey: "user_id" },
      globalIndexes: {
        GoogleUserIdIndex: { hashKey: "google_user_id" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const exportDestinationsTable = new sst.aws.Dynamo("ExportDestinations", {
      fields: {
        destination_id: "string",
        user_id: "string",
      },
      primaryIndex: { hashKey: "destination_id" },
      globalIndexes: {
        UserIdIndex: { hashKey: "user_id" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
        },
      },
    });

    const docsExportsTable = new sst.aws.Dynamo("DocsExports", {
      fields: {
        export_id: "string",
        job_id: "string",
        user_id: "string",
        timestamp: "number",
      },
      primaryIndex: { hashKey: "export_id" },
      globalIndexes: {
        JobIdIndex: { hashKey: "job_id", rangeKey: "timestamp" },
        UserIdIndex: { hashKey: "user_id", rangeKey: "timestamp" },
      },
      transform: {
        table: {
          pointInTimeRecovery: { enabled: true },
          serverSideEncryption: { enabled: true },
          ttl: { attributeName: "ttl", enabled: true },
        },
      },
    });
```

- [ ] **Step 3: Add SQS queue + DLQ**

After the `webhookQueue` declaration (~line 272), insert:

```ts
    const docsExportDlq = new sst.aws.Queue("DocsExportDLQ", {
      transform: {
        queue: {
          messageRetentionSeconds: 1209600, // 14 days
          visibilityTimeoutSeconds: 120,
        },
      },
    });

    const docsExportQueue = new sst.aws.Queue("DocsExportQueue", {
      dlq: {
        queue: docsExportDlq.arn,
        retry: 3,
      },
      transform: {
        queue: {
          visibilityTimeoutSeconds: 120, // matches Lambda timeout
          messageRetentionSeconds: 345600, // 4 days
          receiveWaitTimeSeconds: 20, // long polling
        },
      },
    });
```

- [ ] **Step 4: Wire env vars and links**

In the `sharedEnv` object (~line 333), append:

```ts
      DYNAMODB_GOOGLE_ACCOUNTS_TABLE: googleAccountsTable.name,
      DYNAMODB_EXPORT_DESTINATIONS_TABLE: exportDestinationsTable.name,
      DYNAMODB_DOCS_EXPORTS_TABLE: docsExportsTable.name,
      SQS_DOCS_EXPORT_QUEUE_URL: docsExportQueue.url,
      OAUTH_TOKEN_KMS_KEY_ID: oauthTokenKey.keyId,
      // Google OAuth client (from Doppler)
      GOOGLE_OAUTH_CLIENT_ID: process.env.GOOGLE_OAUTH_CLIENT_ID ?? "",
      GOOGLE_OAUTH_CLIENT_SECRET: process.env.GOOGLE_OAUTH_CLIENT_SECRET ?? "",
      GOOGLE_OAUTH_REDIRECT_URI: process.env.GOOGLE_OAUTH_REDIRECT_URI ?? "",
```

In the `allTables` array (~line 382), append `googleAccountsTable`, `exportDestinationsTable`, `docsExportsTable`.

Update `pythonDefaults.link` (~line 403) to include the new queue:

```ts
      link: [...allTables, jobQueue, webhookQueue, docsExportQueue, resultsBucket],
```

- [ ] **Step 5: Grant KMS permissions to default Lambda config**

In the same `pythonDefaults` block (~line 398), add a `permissions` field if not present, or extend it:

```ts
    const pythonDefaults = {
      runtime: "python3.12" as const,
      memory: "512 MB" as const,
      timeout: "30 seconds" as const,
      environment: sharedEnv,
      link: [...allTables, jobQueue, webhookQueue, docsExportQueue, resultsBucket],
      permissions: [
        {
          actions: ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"],
          resources: [oauthTokenKey.arn],
        },
      ],
    };
```

- [ ] **Step 6: Add Doppler secrets**

Add these three keys to Doppler project `sf-snowscrape` (dev config):
- `GOOGLE_OAUTH_CLIENT_ID` — from Google Cloud Console OAuth client
- `GOOGLE_OAUTH_CLIENT_SECRET` — from Google Cloud Console OAuth client
- `GOOGLE_OAUTH_REDIRECT_URI` — `http://localhost:3001/dashboard/integrations/google/callback` for dev

Run: `doppler secrets set GOOGLE_OAUTH_CLIENT_ID=... --project sf-snowscrape --config dev` (and likewise for the other two)
Expected: Each command echoes the key name with a redacted value preview.

- [ ] **Step 7: Deploy infrastructure**

Run: `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`
Expected: Stack deploys cleanly; output lists `apiUrl`. SST outputs no resource errors.

- [ ] **Step 8: Commit**

```bash
git add sst.config.ts
git commit -m "feat(infra): provision KMS key, 3 DynamoDB tables, SQS queue for Docs export"
```

---

## Phase 2: OAuth Flow

### Task 3: KMS encrypt/decrypt helpers

**Files:**
- Create: `backend/google_oauth.py`
- Test: `backend/tests/unit/test_google_oauth.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_google_oauth.py`:

```python
"""Unit tests for google_oauth module."""
import os
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch):
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


def test_encrypt_token_calls_kms_with_key_id(monkeypatch):
	from google_oauth import encrypt_refresh_token

	fake_kms = MagicMock()
	fake_kms.encrypt.return_value = {"CiphertextBlob": b"ciphertext-bytes"}
	monkeypatch.setattr("google_oauth._kms_client", lambda: fake_kms)

	result = encrypt_refresh_token("plaintext-token")

	fake_kms.encrypt.assert_called_once()
	kwargs = fake_kms.encrypt.call_args.kwargs
	assert kwargs["KeyId"] == "test-key-id"
	assert kwargs["Plaintext"] == b"plaintext-token"
	assert result == "Y2lwaGVydGV4dC1ieXRlcw=="  # base64 of "ciphertext-bytes"


def test_decrypt_token_returns_plaintext(monkeypatch):
	from google_oauth import decrypt_refresh_token

	fake_kms = MagicMock()
	fake_kms.decrypt.return_value = {"Plaintext": b"plaintext-token"}
	monkeypatch.setattr("google_oauth._kms_client", lambda: fake_kms)

	result = decrypt_refresh_token("Y2lwaGVydGV4dC1ieXRlcw==")

	assert result == "plaintext-token"
	fake_kms.decrypt.assert_called_once()
	assert fake_kms.decrypt.call_args.kwargs["CiphertextBlob"] == b"ciphertext-bytes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'google_oauth'`

- [ ] **Step 3: Write the implementation**

Create `backend/google_oauth.py`:

```python
"""
Google OAuth flow helpers.
Handles consent URL generation, code-for-token exchange, token refresh,
and KMS encryption/decryption of refresh tokens.
"""
import base64
import os
from typing import Dict, Optional

import boto3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from logger import get_logger

logger = get_logger(__name__)

OAUTH_SCOPES = [
	"https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/drive.metadata.readonly",
	"https://www.googleapis.com/auth/documents",
	"openid",
	"email",
	"profile",
]


def _kms_client():
	return boto3.client("kms")


def encrypt_refresh_token(plaintext: str) -> str:
	"""Encrypt with KMS; return base64-encoded ciphertext."""
	key_id = os.environ["OAUTH_TOKEN_KMS_KEY_ID"]
	resp = _kms_client().encrypt(KeyId=key_id, Plaintext=plaintext.encode("utf-8"))
	return base64.b64encode(resp["CiphertextBlob"]).decode("ascii")


def decrypt_refresh_token(ciphertext_b64: str) -> str:
	"""Reverse of encrypt_refresh_token."""
	ciphertext = base64.b64decode(ciphertext_b64.encode("ascii"))
	resp = _kms_client().decrypt(CiphertextBlob=ciphertext)
	return resp["Plaintext"].decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/tests/unit/test_google_oauth.py
git commit -m "feat(backend): add KMS encrypt/decrypt helpers for OAuth tokens"
```

---

### Task 4: OAuth consent URL + code exchange

**Files:**
- Modify: `backend/google_oauth.py`
- Modify: `backend/tests/unit/test_google_oauth.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/test_google_oauth.py`:

```python
def test_build_consent_url_includes_state_and_scopes():
	from google_oauth import build_consent_url

	url, state = build_consent_url(user_id="user_123")

	assert "accounts.google.com" in url
	assert "client_id=client-abc" in url
	assert "redirect_uri=http%3A%2F%2Flocalhost%3A3001%2Fcb" in url
	assert "scope=" in url
	assert "access_type=offline" in url
	assert "prompt=consent" in url
	assert state in url
	assert len(state) >= 32


def test_exchange_code_returns_credentials(monkeypatch):
	from google_oauth import exchange_code_for_credentials

	fake_creds = MagicMock(
		token="access-token",
		refresh_token="refresh-token",
		expiry=None,
		scopes=["https://www.googleapis.com/auth/drive.file"],
	)
	fake_flow = MagicMock()
	fake_flow.credentials = fake_creds
	monkeypatch.setattr("google_oauth._build_flow", lambda: fake_flow)

	result = exchange_code_for_credentials(code="auth-code-123")

	fake_flow.fetch_token.assert_called_once_with(code="auth-code-123")
	assert result["access_token"] == "access-token"
	assert result["refresh_token"] == "refresh-token"
	assert "drive.file" in result["scopes"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py::test_build_consent_url_includes_state_and_scopes tests/unit/test_google_oauth.py::test_exchange_code_returns_credentials -v`
Expected: FAIL with `ImportError: cannot import name 'build_consent_url' from 'google_oauth'`

- [ ] **Step 3: Implement**

Append to `backend/google_oauth.py`:

```python
import secrets


def _build_flow() -> Flow:
	client_config = {
		"web": {
			"client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
			"client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
			"auth_uri": "https://accounts.google.com/o/oauth2/auth",
			"token_uri": "https://oauth2.googleapis.com/token",
			"redirect_uris": [os.environ["GOOGLE_OAUTH_REDIRECT_URI"]],
		}
	}
	flow = Flow.from_client_config(client_config, scopes=OAUTH_SCOPES)
	flow.redirect_uri = os.environ["GOOGLE_OAUTH_REDIRECT_URI"]
	return flow


def build_consent_url(user_id: str) -> tuple[str, str]:
	"""Return (consent_url, state). State must be persisted and verified on callback."""
	state = secrets.token_urlsafe(32)
	flow = _build_flow()
	url, _ = flow.authorization_url(
		access_type="offline",
		include_granted_scopes="true",
		prompt="consent",
		state=state,
	)
	return url, state


def exchange_code_for_credentials(code: str) -> Dict:
	"""Exchange authorization code for tokens. Returns dict with access_token, refresh_token, expiry, scopes."""
	flow = _build_flow()
	flow.fetch_token(code=code)
	creds = flow.credentials
	return {
		"access_token": creds.token,
		"refresh_token": creds.refresh_token,
		"expiry": creds.expiry.isoformat() if creds.expiry else None,
		"scopes": list(creds.scopes or []),
	}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/tests/unit/test_google_oauth.py
git commit -m "feat(backend): add Google OAuth consent URL + code exchange"
```

---

### Task 5: Token refresh + Google user info fetch

**Files:**
- Modify: `backend/google_oauth.py`
- Modify: `backend/tests/unit/test_google_oauth.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/test_google_oauth.py`:

```python
def test_refresh_access_token_calls_google(monkeypatch):
	from google_oauth import refresh_access_token

	fake_creds = MagicMock()
	fake_creds.token = "new-access-token"
	fake_creds.expiry = MagicMock()
	fake_creds.expiry.isoformat.return_value = "2026-06-01T12:00:00"

	monkeypatch.setattr(
		"google_oauth.Credentials",
		MagicMock(return_value=fake_creds),
	)
	monkeypatch.setattr("google_oauth.Request", MagicMock())

	result = refresh_access_token(refresh_token="refresh-abc")

	fake_creds.refresh.assert_called_once()
	assert result["access_token"] == "new-access-token"
	assert result["expiry"] == "2026-06-01T12:00:00"


def test_fetch_google_user_info(monkeypatch):
	from google_oauth import fetch_google_user_info

	fake_response = MagicMock()
	fake_response.json.return_value = {
		"sub": "google-user-123",
		"email": "user@example.com",
		"name": "Test User",
	}
	fake_response.raise_for_status.return_value = None

	fake_requests_get = MagicMock(return_value=fake_response)
	monkeypatch.setattr("google_oauth.requests.get", fake_requests_get)

	result = fetch_google_user_info(access_token="access-abc")

	assert result["google_user_id"] == "google-user-123"
	assert result["email"] == "user@example.com"
	assert result["name"] == "Test User"
	called_url = fake_requests_get.call_args.args[0]
	assert "userinfo" in called_url
	headers = fake_requests_get.call_args.kwargs["headers"]
	assert headers["Authorization"] == "Bearer access-abc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py::test_refresh_access_token_calls_google tests/unit/test_google_oauth.py::test_fetch_google_user_info -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Append to `backend/google_oauth.py`:

```python
import requests


def refresh_access_token(refresh_token: str) -> Dict:
	"""Refresh expired access token. Returns dict with access_token, expiry."""
	creds = Credentials(
		token=None,
		refresh_token=refresh_token,
		token_uri="https://oauth2.googleapis.com/token",
		client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
		client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
	)
	creds.refresh(Request())
	return {
		"access_token": creds.token,
		"expiry": creds.expiry.isoformat() if creds.expiry else None,
	}


def fetch_google_user_info(access_token: str) -> Dict:
	"""Call Google userinfo endpoint. Returns dict with google_user_id, email, name."""
	resp = requests.get(
		"https://openidconnect.googleapis.com/v1/userinfo",
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=10,
	)
	resp.raise_for_status()
	data = resp.json()
	return {
		"google_user_id": data["sub"],
		"email": data["email"],
		"name": data.get("name", ""),
	}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_google_oauth.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/tests/unit/test_google_oauth.py
git commit -m "feat(backend): add token refresh + userinfo fetch"
```

---

### Task 6: HTTP handlers — auth-url, callback, list, revoke

**Files:**
- Create: `backend/google_account_handler.py`
- Test: `backend/tests/unit/test_google_account_handler.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_google_account_handler.py`:

```python
"""Unit tests for google_account_handler."""
import json
import os
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("CORS_ALLOWED_ORIGIN", "http://localhost:3001")
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


@pytest.fixture
def dynamo(env):
	with mock_aws():
		client = boto3.resource("dynamodb")
		client.create_table(
			TableName="GoogleAccounts-test",
			KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		yield client


def _auth_event(body=None):
	return {
		"headers": {"Authorization": "Bearer token-x", "origin": "http://localhost:3001"},
		"body": json.dumps(body) if body is not None else None,
	}


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_get_auth_url_returns_consent_url(_mock_clerk, dynamo):
	from google_account_handler import get_auth_url_handler

	resp = get_auth_url_handler(_auth_event(), None)

	assert resp["statusCode"] == 200
	body = json.loads(resp["body"])
	assert body["auth_url"].startswith("https://accounts.google.com")
	assert "state" in body


@patch("google_account_handler.fetch_google_user_info")
@patch("google_account_handler.exchange_code_for_credentials")
@patch("google_account_handler.encrypt_refresh_token", return_value="ciphertext")
@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_callback_persists_account(_clerk, _enc, mock_exchange, mock_userinfo, dynamo):
	from google_account_handler import oauth_callback_handler

	mock_exchange.return_value = {
		"access_token": "at",
		"refresh_token": "rt",
		"expiry": "2026-06-01T12:00:00",
		"scopes": ["https://www.googleapis.com/auth/drive.file"],
	}
	mock_userinfo.return_value = {
		"google_user_id": "g-123",
		"email": "u@example.com",
		"name": "U",
	}
	event = _auth_event({"code": "auth-code-x", "state": "state-x"})

	resp = oauth_callback_handler(event, None)

	assert resp["statusCode"] == 200
	item = dynamo.Table("GoogleAccounts-test").get_item(Key={"user_id": "user_abc"})["Item"]
	assert item["google_user_id"] == "g-123"
	assert item["email"] == "u@example.com"
	assert item["refresh_token_ciphertext"] == "ciphertext"


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_list_returns_connected_account(_clerk, dynamo):
	from google_account_handler import list_google_accounts_handler

	dynamo.Table("GoogleAccounts-test").put_item(Item={
		"user_id": "user_abc",
		"google_user_id": "g-123",
		"email": "u@example.com",
		"name": "U",
		"connected_at": "2026-06-01T00:00:00",
		"refresh_token_ciphertext": "ciphertext",
	})

	resp = list_google_accounts_handler(_auth_event(), None)

	assert resp["statusCode"] == 200
	body = json.loads(resp["body"])
	assert len(body["accounts"]) == 1
	assert body["accounts"][0]["email"] == "u@example.com"
	assert "refresh_token_ciphertext" not in body["accounts"][0]


@patch("google_account_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_revoke_deletes_account(_clerk, dynamo):
	from google_account_handler import revoke_google_account_handler

	dynamo.Table("GoogleAccounts-test").put_item(Item={
		"user_id": "user_abc",
		"google_user_id": "g-123",
		"email": "u@example.com",
		"refresh_token_ciphertext": "ciphertext",
	})

	resp = revoke_google_account_handler(_auth_event(), None)

	assert resp["statusCode"] == 204
	assert "Item" not in dynamo.Table("GoogleAccounts-test").get_item(Key={"user_id": "user_abc"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_google_account_handler.py -v`
Expected: 4 errors — `ModuleNotFoundError: No module named 'google_account_handler'`

- [ ] **Step 3: Implement the handler**

Create `backend/google_account_handler.py`:

```python
"""HTTP handlers for /integrations/google/*."""
import json
import os
from datetime import datetime, timezone

from connection_pool import get_table
from google_oauth import (
	build_consent_url,
	encrypt_refresh_token,
	exchange_code_for_credentials,
	fetch_google_user_info,
)
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

_CORS_ALLOWED_ORIGINS = set(
	o.strip()
	for o in os.environ.get("CORS_ALLOWED_ORIGIN", "http://localhost:3001").split(",")
	if o.strip()
)


def _cors_origin(event):
	headers = (event or {}).get("headers") or {}
	origin = headers.get("origin") or headers.get("Origin", "")
	if origin in _CORS_ALLOWED_ORIGINS:
		return origin
	return next(iter(_CORS_ALLOWED_ORIGINS))


def _response(status, body, event=None):
	if status == 204:
		return {"statusCode": 204, "body": "", "headers": _headers(event)}
	return {"statusCode": status, "body": json.dumps(body), "headers": _headers(event)}


def _headers(event):
	return {
		"Content-Type": "application/json",
		"Access-Control-Allow-Origin": _cors_origin(event),
		"Access-Control-Allow-Credentials": True,
	}


def _authenticate(event):
	token = extract_token_from_event(event)
	if not token:
		return None, _response(401, {"message": "Unauthorized"}, event)
	try:
		user_data = validate_clerk_token(token)
		return user_data, None
	except Exception as e:
		return None, _response(401, {"message": str(e)}, event)


def _table():
	return get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])


def get_auth_url_handler(event, context):
	"""GET /integrations/google/auth-url"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	url, state = build_consent_url(user_id=user_data["sub"])
	return _response(200, {"auth_url": url, "state": state}, event)


def oauth_callback_handler(event, context):
	"""POST /integrations/google/callback {code, state}"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	body = json.loads(event.get("body") or "{}")
	code = body.get("code")
	if not code:
		return _response(400, {"message": "code is required"}, event)
	try:
		creds = exchange_code_for_credentials(code=code)
	except Exception as e:
		logger.error("OAuth token exchange failed", error=str(e))
		return _response(400, {"message": "Failed to exchange code"}, event)

	if not creds.get("refresh_token"):
		return _response(400, {"message": "No refresh token returned; user must re-consent"}, event)

	user_info = fetch_google_user_info(creds["access_token"])
	ciphertext = encrypt_refresh_token(creds["refresh_token"])

	_table().put_item(Item={
		"user_id": user_data["sub"],
		"google_user_id": user_info["google_user_id"],
		"email": user_info["email"],
		"name": user_info["name"],
		"refresh_token_ciphertext": ciphertext,
		"scopes": creds["scopes"],
		"connected_at": datetime.now(timezone.utc).isoformat(),
	})
	return _response(200, {"email": user_info["email"], "name": user_info["name"]}, event)


def list_google_accounts_handler(event, context):
	"""GET /integrations/google"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	item = _table().get_item(Key={"user_id": user_data["sub"]}).get("Item")
	if not item:
		return _response(200, {"accounts": []}, event)
	return _response(200, {"accounts": [{
		"google_user_id": item["google_user_id"],
		"email": item["email"],
		"name": item.get("name", ""),
		"connected_at": item.get("connected_at"),
	}]}, event)


def revoke_google_account_handler(event, context):
	"""DELETE /integrations/google"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	_table().delete_item(Key={"user_id": user_data["sub"]})
	return _response(204, None, event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_google_account_handler.py -v`
Expected: 4 passed.

- [ ] **Step 5: Wire routes in SST**

In `sst.config.ts`, after the API Keys routes (~line 643), add:

```ts
    // Google Account Integration
    api.route("GET /integrations/google/auth-url", {
      ...pythonDefaults,
      handler: "backend/google_account_handler.get_auth_url_handler",
      timeout: "10 seconds",
    });

    api.route("POST /integrations/google/callback", {
      ...pythonDefaults,
      handler: "backend/google_account_handler.oauth_callback_handler",
      timeout: "30 seconds",
    });

    api.route("GET /integrations/google", {
      ...pythonDefaults,
      handler: "backend/google_account_handler.list_google_accounts_handler",
      timeout: "10 seconds",
    });

    api.route("DELETE /integrations/google", {
      ...pythonDefaults,
      handler: "backend/google_account_handler.revoke_google_account_handler",
      timeout: "10 seconds",
    });
```

- [ ] **Step 6: Deploy**

Run: `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`
Expected: 4 new routes appear in the SST output.

- [ ] **Step 7: Commit**

```bash
git add backend/google_account_handler.py backend/tests/unit/test_google_account_handler.py sst.config.ts
git commit -m "feat(backend): add Google account OAuth handlers + routes"
```

---

## Phase 3: Export Destination CRUD

### Task 7: Destination handler — create + list + get + delete

**Files:**
- Create: `backend/export_destination_handler.py`
- Test: `backend/tests/unit/test_export_destination_handler.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_export_destination_handler.py`:

```python
"""Unit tests for export_destination_handler."""
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("CORS_ALLOWED_ORIGIN", "http://localhost:3001")


@pytest.fixture
def dynamo(env):
	with mock_aws():
		client = boto3.resource("dynamodb")
		client.create_table(
			TableName="ExportDestinations-test",
			KeySchema=[{"AttributeName": "destination_id", "KeyType": "HASH"}],
			AttributeDefinitions=[
				{"AttributeName": "destination_id", "AttributeType": "S"},
				{"AttributeName": "user_id", "AttributeType": "S"},
			],
			GlobalSecondaryIndexes=[{
				"IndexName": "UserIdIndex",
				"KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
				"Projection": {"ProjectionType": "ALL"},
			}],
			BillingMode="PAY_PER_REQUEST",
		)
		client.create_table(
			TableName="GoogleAccounts-test",
			KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		client.Table("GoogleAccounts-test").put_item(Item={
			"user_id": "user_abc",
			"google_user_id": "g-123",
			"email": "u@example.com",
			"refresh_token_ciphertext": "x",
		})
		yield client


def _auth_event(body=None, path_params=None):
	return {
		"headers": {"Authorization": "Bearer t", "origin": "http://localhost:3001"},
		"body": json.dumps(body) if body is not None else None,
		"pathParameters": path_params or {},
	}


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_create_destination_persists(_clerk, dynamo):
	from export_destination_handler import create_destination_handler

	resp = create_destination_handler(_auth_event({
		"name": "My LinkedIn export",
		"type": "google_docs",
		"drive_folder_id": "folder-xyz",
		"naming_template": "{{job_name}} — {{date}}",
		"mode": "new_doc_per_run",
		"format_template": "structured_log",
	}), None)

	assert resp["statusCode"] == 201
	body = json.loads(resp["body"])
	assert body["name"] == "My LinkedIn export"
	assert "destination_id" in body

	items = dynamo.Table("ExportDestinations-test").scan()["Items"]
	assert len(items) == 1
	assert items[0]["user_id"] == "user_abc"
	assert items[0]["drive_folder_id"] == "folder-xyz"


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_create_destination_rejects_without_google_account(_clerk, dynamo):
	from export_destination_handler import create_destination_handler

	dynamo.Table("GoogleAccounts-test").delete_item(Key={"user_id": "user_abc"})

	resp = create_destination_handler(_auth_event({
		"name": "x",
		"type": "google_docs",
		"drive_folder_id": "f",
		"naming_template": "{{date}}",
		"mode": "new_doc_per_run",
		"format_template": "structured_log",
	}), None)

	assert resp["statusCode"] == 400
	assert "google account" in json.loads(resp["body"])["message"].lower()


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_list_returns_only_users_destinations(_clerk, dynamo):
	from export_destination_handler import list_destinations_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-2", "user_id": "other_user", "name": "Theirs",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = list_destinations_handler(_auth_event(), None)

	body = json.loads(resp["body"])
	assert len(body["destinations"]) == 1
	assert body["destinations"][0]["name"] == "Mine"


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_delete_destination(_clerk, dynamo):
	from export_destination_handler import delete_destination_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = delete_destination_handler(
		_auth_event(path_params={"destination_id": "d-1"}),
		None,
	)

	assert resp["statusCode"] == 204
	assert "Item" not in dynamo.Table("ExportDestinations-test").get_item(Key={"destination_id": "d-1"})


@patch("export_destination_handler.validate_clerk_token", return_value={"sub": "user_abc"})
def test_delete_other_users_destination_forbidden(_clerk, dynamo):
	from export_destination_handler import delete_destination_handler

	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "other_user", "name": "Theirs",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
	})

	resp = delete_destination_handler(
		_auth_event(path_params={"destination_id": "d-1"}),
		None,
	)

	assert resp["statusCode"] == 404
	assert "Item" in dynamo.Table("ExportDestinations-test").get_item(Key={"destination_id": "d-1"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_export_destination_handler.py -v`
Expected: 5 errors — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `backend/export_destination_handler.py`:

```python
"""HTTP handlers for /export-destinations."""
import json
import os
import uuid
from datetime import datetime, timezone

from connection_pool import get_table
from logger import get_logger, log_lambda_invocation
from utils import extract_token_from_event, validate_clerk_token

logger = get_logger(__name__)

VALID_TYPES = {"google_docs"}
VALID_MODES = {"new_doc_per_run", "one_doc_per_row"}
VALID_FORMATS = {"structured_log", "compact_list", "narrative"}
MAX_NAME_LEN = 100
MAX_TEMPLATE_LEN = 200

_CORS_ALLOWED_ORIGINS = set(
	o.strip()
	for o in os.environ.get("CORS_ALLOWED_ORIGIN", "http://localhost:3001").split(",")
	if o.strip()
)


def _cors_origin(event):
	headers = (event or {}).get("headers") or {}
	origin = headers.get("origin") or headers.get("Origin", "")
	if origin in _CORS_ALLOWED_ORIGINS:
		return origin
	return next(iter(_CORS_ALLOWED_ORIGINS))


def _headers(event):
	return {
		"Content-Type": "application/json",
		"Access-Control-Allow-Origin": _cors_origin(event),
		"Access-Control-Allow-Credentials": True,
	}


def _response(status, body, event=None):
	if status == 204:
		return {"statusCode": 204, "body": "", "headers": _headers(event)}
	return {"statusCode": status, "body": json.dumps(body), "headers": _headers(event)}


def _authenticate(event):
	token = extract_token_from_event(event)
	if not token:
		return None, _response(401, {"message": "Unauthorized"}, event)
	try:
		return validate_clerk_token(token), None
	except Exception as e:
		return None, _response(401, {"message": str(e)}, event)


def _destinations_table():
	return get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])


def _google_accounts_table():
	return get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])


def _validate_body(body):
	name = (body.get("name") or "").strip()
	if not name or len(name) > MAX_NAME_LEN:
		return f"name must be 1-{MAX_NAME_LEN} chars"
	if body.get("type") not in VALID_TYPES:
		return f"type must be one of {sorted(VALID_TYPES)}"
	if not body.get("drive_folder_id"):
		return "drive_folder_id is required"
	tmpl = body.get("naming_template", "")
	if not tmpl or len(tmpl) > MAX_TEMPLATE_LEN:
		return f"naming_template must be 1-{MAX_TEMPLATE_LEN} chars"
	if body.get("mode") not in VALID_MODES:
		return f"mode must be one of {sorted(VALID_MODES)}"
	if body.get("format_template") not in VALID_FORMATS:
		return f"format_template must be one of {sorted(VALID_FORMATS)}"
	return None


def create_destination_handler(event, context):
	"""POST /export-destinations"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	user_id = user_data["sub"]
	body = json.loads(event.get("body") or "{}")
	msg = _validate_body(body)
	if msg:
		return _response(400, {"message": msg}, event)

	account = _google_accounts_table().get_item(Key={"user_id": user_id}).get("Item")
	if not account:
		return _response(400, {"message": "No Google account connected. Connect one first."}, event)

	destination_id = f"dst_{uuid.uuid4().hex[:16]}"
	item = {
		"destination_id": destination_id,
		"user_id": user_id,
		"name": body["name"].strip(),
		"type": body["type"],
		"google_user_id": account["google_user_id"],
		"drive_folder_id": body["drive_folder_id"],
		"naming_template": body["naming_template"],
		"mode": body["mode"],
		"format_template": body["format_template"],
		"created_at": datetime.now(timezone.utc).isoformat(),
	}
	_destinations_table().put_item(Item=item)
	return _response(201, item, event)


def list_destinations_handler(event, context):
	"""GET /export-destinations"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	resp = _destinations_table().query(
		IndexName="UserIdIndex",
		KeyConditionExpression="user_id = :uid",
		ExpressionAttributeValues={":uid": user_data["sub"]},
	)
	return _response(200, {"destinations": resp.get("Items", [])}, event)


def delete_destination_handler(event, context):
	"""DELETE /export-destinations/{destination_id}"""
	log_lambda_invocation(event, context, logger)
	user_data, err = _authenticate(event)
	if err:
		return err
	destination_id = (event.get("pathParameters") or {}).get("destination_id")
	if not destination_id:
		return _response(400, {"message": "destination_id required"}, event)
	existing = _destinations_table().get_item(Key={"destination_id": destination_id}).get("Item")
	if not existing or existing.get("user_id") != user_data["sub"]:
		return _response(404, {"message": "Destination not found"}, event)
	_destinations_table().delete_item(Key={"destination_id": destination_id})
	return _response(204, None, event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_export_destination_handler.py -v`
Expected: 5 passed.

- [ ] **Step 5: Wire routes in SST**

After the Google integration routes in `sst.config.ts`, add:

```ts
    // Export Destinations
    api.route("POST /export-destinations", {
      ...pythonDefaults,
      handler: "backend/export_destination_handler.create_destination_handler",
      timeout: "10 seconds",
    });

    api.route("GET /export-destinations", {
      ...pythonDefaults,
      handler: "backend/export_destination_handler.list_destinations_handler",
      timeout: "10 seconds",
    });

    api.route("DELETE /export-destinations/{destination_id}", {
      ...pythonDefaults,
      handler: "backend/export_destination_handler.delete_destination_handler",
      timeout: "10 seconds",
    });
```

- [ ] **Step 6: Deploy**

Run: `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`
Expected: 3 new routes in output.

- [ ] **Step 7: Commit**

```bash
git add backend/export_destination_handler.py backend/tests/unit/test_export_destination_handler.py sst.config.ts
git commit -m "feat(backend): add export destination CRUD + routes"
```

---

## Phase 4: Export Pipeline (Formatter + Dispatcher + Lambda)

### Task 8: Docs formatter — pure function

**Files:**
- Create: `backend/docs_formatter.py`
- Test: `backend/tests/unit/test_docs_formatter.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_docs_formatter.py`:

```python
"""Unit tests for docs_formatter."""
import pytest


def test_structured_log_emits_heading_per_row():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"url": "https://a.example/post/1", "title": "First post", "body": "Hello"},
		{"url": "https://a.example/post/2", "title": "Second post", "body": "World"},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="structured_log",
		title="My Job — 2026-06-01",
	)

	assert any(
		"insertText" in r and "My Job — 2026-06-01" in r["insertText"]["text"]
		for r in requests
	)
	assert any("First post" in r.get("insertText", {}).get("text", "") for r in requests)
	assert any("Second post" in r.get("insertText", {}).get("text", "") for r in requests)
	assert any("updateParagraphStyle" in r for r in requests)


def test_compact_list_one_line_per_row():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"url": "https://a/1", "title": "A"},
		{"url": "https://a/2", "title": "B"},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="compact_list",
		title="Compact",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "A" in full_text
	assert "B" in full_text
	assert full_text.count("\n") <= len(rows) + 3  # title + bullets, no per-field blocks


def test_narrative_concatenates_body_fields():
	from docs_formatter import format_rows_to_docs_requests

	rows = [
		{"body": "Paragraph one."},
		{"body": "Paragraph two."},
	]

	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template="narrative",
		title="Narrative",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "Paragraph one." in full_text
	assert "Paragraph two." in full_text


def test_empty_rows_still_produces_title():
	from docs_formatter import format_rows_to_docs_requests

	requests = format_rows_to_docs_requests(
		rows=[],
		format_template="structured_log",
		title="Empty Job",
	)

	full_text = "".join(
		r.get("insertText", {}).get("text", "") for r in requests
	)
	assert "Empty Job" in full_text
	assert "No results" in full_text


def test_invalid_template_raises():
	from docs_formatter import format_rows_to_docs_requests

	with pytest.raises(ValueError, match="format_template"):
		format_rows_to_docs_requests(rows=[], format_template="bogus", title="x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_docs_formatter.py -v`
Expected: 5 errors — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `backend/docs_formatter.py`:

```python
"""Pure functions for converting scrape rows into Google Docs batchUpdate requests.

Each format_template emits a list of dicts matching the Docs API request schema:
https://developers.google.com/docs/api/reference/rest/v1/documents/request
"""
from typing import Dict, List

VALID_TEMPLATES = {"structured_log", "compact_list", "narrative"}


def _insert_text(text: str, index: int) -> dict:
	return {"insertText": {"location": {"index": index}, "text": text}}


def _heading_style(start: int, end: int, level: str) -> dict:
	return {
		"updateParagraphStyle": {
			"range": {"startIndex": start, "endIndex": end},
			"paragraphStyle": {"namedStyleType": level},
			"fields": "namedStyleType",
		}
	}


def format_rows_to_docs_requests(
	rows: List[Dict],
	format_template: str,
	title: str,
) -> List[dict]:
	if format_template not in VALID_TEMPLATES:
		raise ValueError(f"format_template must be one of {sorted(VALID_TEMPLATES)}")

	# Build the full text first; emit a single insertText, then style runs.
	# Docs API inserts at index 1 (after the document's implicit initial char).
	if format_template == "structured_log":
		return _build_structured_log(rows, title)
	if format_template == "compact_list":
		return _build_compact_list(rows, title)
	return _build_narrative(rows, title)


def _build_structured_log(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	text = f"{title}\n"
	requests.append(_insert_text(text, index))
	title_end = index + len(text)
	requests.append(_heading_style(index, title_end - 1, "TITLE"))
	index = title_end

	if not rows:
		body = "No results found.\n"
		requests.append(_insert_text(body, index))
		return requests

	for row in rows:
		row_title = str(row.get("title") or row.get("url") or "(untitled)")
		heading_text = f"{row_title}\n"
		requests.append(_insert_text(heading_text, index))
		heading_end = index + len(heading_text)
		requests.append(_heading_style(index, heading_end - 1, "HEADING_2"))
		index = heading_end

		field_lines: List[str] = []
		for key, value in row.items():
			if key in ("title",):
				continue
			field_lines.append(f"{key}: {value}")
		block = "\n".join(field_lines) + "\n\n"
		requests.append(_insert_text(block, index))
		index += len(block)

	return requests


def _build_compact_list(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	header = f"{title}\n"
	requests.append(_insert_text(header, index))
	requests.append(_heading_style(index, index + len(header) - 1, "TITLE"))
	index += len(header)

	if not rows:
		text = "No results found.\n"
		requests.append(_insert_text(text, index))
		return requests

	body_lines: List[str] = []
	for row in rows:
		label = row.get("title") or row.get("url") or "(untitled)"
		body_lines.append(f"• {label}")
	text = "\n".join(body_lines) + "\n"
	requests.append(_insert_text(text, index))
	return requests


def _build_narrative(rows: List[Dict], title: str) -> List[dict]:
	requests: List[dict] = []
	index = 1
	header = f"{title}\n"
	requests.append(_insert_text(header, index))
	requests.append(_heading_style(index, index + len(header) - 1, "TITLE"))
	index += len(header)

	if not rows:
		text = "No results found.\n"
		requests.append(_insert_text(text, index))
		return requests

	paragraphs: List[str] = []
	for row in rows:
		body = row.get("body") or row.get("text") or row.get("content") or ""
		if body:
			paragraphs.append(str(body))
	text = "\n\n".join(paragraphs) + "\n"
	requests.append(_insert_text(text, index))
	return requests
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_docs_formatter.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/docs_formatter.py backend/tests/unit/test_docs_formatter.py
git commit -m "feat(backend): add Google Docs batchUpdate formatter"
```

---

### Task 9: DocsExporter — dispatch SQS messages on job completion

**Files:**
- Create: `backend/docs_exporter.py`
- Test: `backend/tests/unit/test_docs_exporter.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/test_docs_exporter.py`:

```python
"""Unit tests for DocsExporter."""
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", "https://sqs.test/queue")


@pytest.fixture
def aws_setup(env):
	with mock_aws():
		dynamo = boto3.resource("dynamodb")
		dynamo.create_table(
			TableName="ExportDestinations-test",
			KeySchema=[{"AttributeName": "destination_id", "KeyType": "HASH"}],
			AttributeDefinitions=[{"AttributeName": "destination_id", "AttributeType": "S"}],
			BillingMode="PAY_PER_REQUEST",
		)
		sqs = boto3.client("sqs")
		queue_url = sqs.create_queue(QueueName="docs-export-test")["QueueUrl"]
		yield {"dynamo": dynamo, "sqs": sqs, "queue_url": queue_url}


def test_dispatch_skips_when_no_destinations(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=[],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)
	assert count == 0


def test_dispatch_sends_one_message_per_destination(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	dynamo = aws_setup["dynamo"]
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-1", "user_id": "user_abc", "name": "A",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "structured_log",
		"google_user_id": "g-123",
	})
	dynamo.Table("ExportDestinations-test").put_item(Item={
		"destination_id": "d-2", "user_id": "user_abc", "name": "B",
		"type": "google_docs", "drive_folder_id": "f", "naming_template": "{{date}}",
		"mode": "new_doc_per_run", "format_template": "compact_list",
		"google_user_id": "g-123",
	})

	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["d-1", "d-2"],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)

	assert count == 2
	messages = aws_setup["sqs"].receive_message(
		QueueUrl=aws_setup["queue_url"],
		MaxNumberOfMessages=10,
	).get("Messages", [])
	assert len(messages) == 2
	parsed = [json.loads(m["Body"]) for m in messages]
	dest_ids = sorted(m["destination_id"] for m in parsed)
	assert dest_ids == ["d-1", "d-2"]
	for m in parsed:
		assert m["job_id"] == "job-1"
		assert m["user_id"] == "user_abc"
		assert m["results_s3_key"] == "results/job-1.json"
		assert "export_id" in m


def test_dispatch_ignores_missing_destination_ids(aws_setup, monkeypatch):
	monkeypatch.setenv("SQS_DOCS_EXPORT_QUEUE_URL", aws_setup["queue_url"])
	from docs_exporter import DocsExporter

	count = DocsExporter.dispatch_job_completed(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["missing-d"],
		results_s3_key="results/job-1.json",
		job_data={"name": "Test"},
	)
	assert count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/unit/test_docs_exporter.py -v`
Expected: 3 errors — `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `backend/docs_exporter.py`:

```python
"""Dispatcher that fans Docs export messages to SQS, mirroring webhook_dispatcher."""
import json
import os
import uuid
from typing import Dict, List

import boto3

from connection_pool import get_table
from logger import get_logger

logger = get_logger(__name__)


class DocsExporter:
	"""Dispatches Google Docs export messages to SQS for async delivery."""

	@staticmethod
	def dispatch_job_completed(
		job_id: str,
		user_id: str,
		destination_ids: List[str],
		results_s3_key: str,
		job_data: Dict,
	) -> int:
		"""Returns the number of export messages sent."""
		if not destination_ids:
			return 0

		table = get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])
		sqs = boto3.client("sqs")
		queue_url = os.environ["SQS_DOCS_EXPORT_QUEUE_URL"]

		sent = 0
		for destination_id in destination_ids:
			item = table.get_item(Key={"destination_id": destination_id}).get("Item")
			if not item or item.get("user_id") != user_id:
				logger.warning(
					"Destination missing or owned by another user",
					destination_id=destination_id, user_id=user_id,
				)
				continue
			export_id = f"exp_{uuid.uuid4().hex[:16]}"
			message = {
				"export_id": export_id,
				"destination_id": destination_id,
				"job_id": job_id,
				"user_id": user_id,
				"results_s3_key": results_s3_key,
				"job_name": job_data.get("name", ""),
			}
			try:
				sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
				sent += 1
				logger.info(
					"Docs export dispatched",
					export_id=export_id, destination_id=destination_id, job_id=job_id,
				)
			except Exception as e:
				logger.error(
					"Failed to dispatch Docs export",
					export_id=export_id, destination_id=destination_id, error=str(e),
				)
		return sent
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/unit/test_docs_exporter.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/docs_exporter.py backend/tests/unit/test_docs_exporter.py
git commit -m "feat(backend): add DocsExporter SQS dispatcher"
```

---

### Task 10: SQS-triggered Lambda — write to Google Docs

**Files:**
- Create: `backend/docs_export_handler.py`
- Test: `backend/tests/integration/test_docs_export_flow.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_docs_export_flow.py`:

```python
"""Integration test for SQS-triggered Docs export Lambda."""
import json
from unittest.mock import patch, MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def env(monkeypatch):
	monkeypatch.setenv("DYNAMODB_EXPORT_DESTINATIONS_TABLE", "ExportDestinations-test")
	monkeypatch.setenv("DYNAMODB_GOOGLE_ACCOUNTS_TABLE", "GoogleAccounts-test")
	monkeypatch.setenv("DYNAMODB_DOCS_EXPORTS_TABLE", "DocsExports-test")
	monkeypatch.setenv("S3_BUCKET", "results-test")
	monkeypatch.setenv("OAUTH_TOKEN_KMS_KEY_ID", "test-key-id")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-abc")
	monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret-xyz")
	monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3001/cb")


@pytest.fixture
def aws_resources(env):
	with mock_aws():
		dynamo = boto3.resource("dynamodb")
		for name, fields in [
			("ExportDestinations-test", [("destination_id", "S")]),
			("GoogleAccounts-test", [("user_id", "S")]),
			("DocsExports-test", [("export_id", "S")]),
		]:
			dynamo.create_table(
				TableName=name,
				KeySchema=[{"AttributeName": fields[0][0], "KeyType": "HASH"}],
				AttributeDefinitions=[{"AttributeName": f[0], "AttributeType": f[1]} for f in fields],
				BillingMode="PAY_PER_REQUEST",
			)
		s3 = boto3.client("s3")
		s3.create_bucket(
			Bucket="results-test",
			CreateBucketConfiguration={"LocationConstraint": "us-east-2"},
		)
		s3.put_object(
			Bucket="results-test",
			Key="results/job-1.json",
			Body=json.dumps([
				{"url": "https://a/1", "title": "Post 1", "body": "Hello"},
				{"url": "https://a/2", "title": "Post 2", "body": "World"},
			]).encode("utf-8"),
		)
		dynamo.Table("ExportDestinations-test").put_item(Item={
			"destination_id": "d-1", "user_id": "user_abc", "name": "Mine",
			"type": "google_docs", "drive_folder_id": "folder-xyz",
			"naming_template": "{{job_name}} — {{date}}",
			"mode": "new_doc_per_run", "format_template": "structured_log",
			"google_user_id": "g-123",
		})
		dynamo.Table("GoogleAccounts-test").put_item(Item={
			"user_id": "user_abc", "google_user_id": "g-123",
			"email": "u@example.com", "refresh_token_ciphertext": "ciphertext",
		})
		yield {"dynamo": dynamo, "s3": s3}


@patch("docs_export_handler.decrypt_refresh_token", return_value="refresh-token-plain")
@patch("docs_export_handler._build_drive_service")
@patch("docs_export_handler._build_docs_service")
@patch("docs_export_handler.refresh_access_token")
def test_export_creates_doc_and_logs(
	mock_refresh, mock_docs, mock_drive, _mock_decrypt, aws_resources,
):
	mock_refresh.return_value = {"access_token": "access-fresh", "expiry": "2026-06-01T13:00:00"}
	mock_drive.return_value.files.return_value.create.return_value.execute.return_value = {
		"id": "doc-id-123", "webViewLink": "https://docs.google.com/document/d/doc-id-123",
	}
	mock_docs.return_value.documents.return_value.batchUpdate.return_value.execute.return_value = {}

	from docs_export_handler import docs_export_handler

	sqs_event = {"Records": [{
		"messageId": "msg-1",
		"body": json.dumps({
			"export_id": "exp-1",
			"destination_id": "d-1",
			"job_id": "job-1",
			"user_id": "user_abc",
			"results_s3_key": "results/job-1.json",
			"job_name": "Test Job",
		}),
	}]}

	result = docs_export_handler(sqs_event, None)

	assert result.get("batchItemFailures", []) == []
	mock_drive.return_value.files.return_value.create.assert_called_once()
	create_kwargs = mock_drive.return_value.files.return_value.create.call_args.kwargs
	assert create_kwargs["body"]["parents"] == ["folder-xyz"]
	assert "Test Job" in create_kwargs["body"]["name"]
	mock_docs.return_value.documents.return_value.batchUpdate.assert_called_once()

	log = aws_resources["dynamo"].Table("DocsExports-test").get_item(Key={"export_id": "exp-1"})["Item"]
	assert log["status"] == "success"
	assert log["doc_id"] == "doc-id-123"
	assert log["doc_url"] == "https://docs.google.com/document/d/doc-id-123"


@patch("docs_export_handler.decrypt_refresh_token", return_value="refresh-token-plain")
@patch("docs_export_handler._build_drive_service")
@patch("docs_export_handler._build_docs_service")
@patch("docs_export_handler.refresh_access_token")
def test_export_returns_failure_on_api_error(
	mock_refresh, mock_docs, mock_drive, _mock_decrypt, aws_resources,
):
	mock_refresh.return_value = {"access_token": "at", "expiry": None}
	mock_drive.return_value.files.return_value.create.return_value.execute.side_effect = RuntimeError("api boom")

	from docs_export_handler import docs_export_handler

	sqs_event = {"Records": [{
		"messageId": "msg-1",
		"body": json.dumps({
			"export_id": "exp-1",
			"destination_id": "d-1",
			"job_id": "job-1",
			"user_id": "user_abc",
			"results_s3_key": "results/job-1.json",
			"job_name": "Test Job",
		}),
	}]}

	result = docs_export_handler(sqs_event, None)

	assert result["batchItemFailures"] == [{"itemIdentifier": "msg-1"}]
	log = aws_resources["dynamo"].Table("DocsExports-test").get_item(Key={"export_id": "exp-1"})["Item"]
	assert log["status"] == "failed"
	assert "api boom" in log["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/integration/test_docs_export_flow.py -v`
Expected: 2 errors — `ModuleNotFoundError: No module named 'docs_export_handler'`.

- [ ] **Step 3: Implement**

Create `backend/docs_export_handler.py`:

```python
"""SQS-triggered Lambda that writes scrape results to Google Docs."""
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict

import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from connection_pool import get_table
from docs_formatter import format_rows_to_docs_requests
from google_oauth import decrypt_refresh_token, refresh_access_token
from logger import get_logger

logger = get_logger(__name__)


def _build_drive_service(access_token: str):
	creds = Credentials(token=access_token)
	return build("drive", "v3", credentials=creds, cache_discovery=False)


def _build_docs_service(access_token: str):
	creds = Credentials(token=access_token)
	return build("docs", "v1", credentials=creds, cache_discovery=False)


def _read_results(s3_key: str):
	s3 = boto3.client("s3")
	bucket = os.environ["S3_BUCKET"]
	obj = s3.get_object(Bucket=bucket, Key=s3_key)
	data = json.loads(obj["Body"].read())
	return data if isinstance(data, list) else data.get("rows", [])


def _render_doc_title(naming_template: str, job_name: str) -> str:
	date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
	return (
		naming_template
		.replace("{{job_name}}", job_name or "")
		.replace("{{date}}", date_str)
	)


def _log_export(export_id: str, status: str, *, doc_id="", doc_url="", error=""):
	table = get_table(os.environ["DYNAMODB_DOCS_EXPORTS_TABLE"])
	table.put_item(Item={
		"export_id": export_id,
		"status": status,
		"doc_id": doc_id,
		"doc_url": doc_url,
		"error": error[:1000],
		"timestamp": int(time.time()),
		"created_at": datetime.now(timezone.utc).isoformat(),
		"ttl": int(time.time()) + 60 * 60 * 24 * 90,
	})


def _process_one(message: Dict) -> None:
	export_id = message["export_id"]
	destination_id = message["destination_id"]
	user_id = message["user_id"]
	job_name = message.get("job_name", "")

	destinations = get_table(os.environ["DYNAMODB_EXPORT_DESTINATIONS_TABLE"])
	dest = destinations.get_item(Key={"destination_id": destination_id}).get("Item")
	if not dest or dest.get("user_id") != user_id:
		raise RuntimeError(f"Destination {destination_id} not found for user {user_id}")

	accounts = get_table(os.environ["DYNAMODB_GOOGLE_ACCOUNTS_TABLE"])
	account = accounts.get_item(Key={"user_id": user_id}).get("Item")
	if not account:
		raise RuntimeError(f"No Google account for user {user_id}")

	refresh_token = decrypt_refresh_token(account["refresh_token_ciphertext"])
	tokens = refresh_access_token(refresh_token=refresh_token)
	access_token = tokens["access_token"]

	rows = _read_results(message["results_s3_key"])
	title = _render_doc_title(dest["naming_template"], job_name)

	drive = _build_drive_service(access_token)
	created = drive.files().create(
		body={
			"name": title,
			"mimeType": "application/vnd.google-apps.document",
			"parents": [dest["drive_folder_id"]],
		},
		fields="id, webViewLink",
	).execute()
	doc_id = created["id"]
	doc_url = created["webViewLink"]

	docs = _build_docs_service(access_token)
	requests = format_rows_to_docs_requests(
		rows=rows,
		format_template=dest["format_template"],
		title=title,
	)
	docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

	_log_export(export_id, "success", doc_id=doc_id, doc_url=doc_url)


def docs_export_handler(event, context):
	"""SQS handler. Uses partial batch responses for retry."""
	failed: list = []
	for record in event.get("Records", []):
		message_id = record.get("messageId", "")
		try:
			message = json.loads(record["body"])
			_process_one(message)
		except Exception as e:
			logger.error("Docs export failed", error=str(e), message_id=message_id)
			try:
				body = json.loads(record.get("body") or "{}")
				_log_export(
					body.get("export_id", message_id),
					"failed",
					error=str(e),
				)
			except Exception:
				logger.error("Could not log failure", message_id=message_id)
			failed.append({"itemIdentifier": message_id})
	return {"batchItemFailures": failed}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/integration/test_docs_export_flow.py -v`
Expected: 2 passed.

- [ ] **Step 5: Wire SQS subscriber in SST**

In `sst.config.ts`, after the `webhookQueue.subscribe(...)` block (~line 716), add:

```ts
    docsExportQueue.subscribe(
      {
        ...pythonDefaults,
        handler: "backend/docs_export_handler.docs_export_handler",
        memory: "512 MB",
        timeout: "120 seconds",
      },
      {
        batch: {
          size: 5,
          partialResponses: true,
        },
      },
    );
```

- [ ] **Step 6: Deploy**

Run: `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`
Expected: New `DocsExportQueueSubscriber` Lambda in SST output.

- [ ] **Step 7: Commit**

```bash
git add backend/docs_export_handler.py backend/tests/integration/test_docs_export_flow.py sst.config.ts
git commit -m "feat(backend): add SQS-triggered Docs export Lambda"
```

---

## Phase 5: Job Wiring

### Task 11: Attach destinations to jobs + fan out on completion

**Files:**
- Modify: `backend/job_manager.py`
- Modify: `backend/tests/unit/` (locate existing job_manager test file, or create one)

- [ ] **Step 1: Inspect existing job completion path**

Run: `grep -n "dispatch_job_completed" backend/job_manager.py`
Expected: One or more line numbers showing where the webhook dispatch is called. Note them — you'll add the Docs dispatch call immediately after each.

- [ ] **Step 2: Write the failing test**

Locate an existing test (e.g., `backend/tests/integration/test_handlers.py`) or create `backend/tests/unit/test_job_manager_docs_dispatch.py`:

```python
"""Verify Docs export fan-out runs on job completion."""
import json
from unittest.mock import patch, MagicMock


@patch("job_manager.DocsExporter")
@patch("job_manager.WebhookDispatcher")
def test_completion_dispatches_to_docs_exporter(mock_webhook, mock_docs):
	"""Job with export_destination_ids dispatches to both webhook + docs."""
	from job_manager import _on_job_completed  # helper added in this task

	job_data = {
		"job_id": "job-1",
		"user_id": "user_abc",
		"name": "Test Job",
		"export_destination_ids": ["d-1", "d-2"],
		"results_s3_key": "results/job-1.json",
	}

	_on_job_completed(job_data=job_data, results_summary={"rows": 5})

	mock_webhook.dispatch_job_completed.assert_called_once()
	mock_docs.dispatch_job_completed.assert_called_once_with(
		job_id="job-1",
		user_id="user_abc",
		destination_ids=["d-1", "d-2"],
		results_s3_key="results/job-1.json",
		job_data=job_data,
	)


@patch("job_manager.DocsExporter")
@patch("job_manager.WebhookDispatcher")
def test_completion_skips_docs_when_no_destinations(mock_webhook, mock_docs):
	from job_manager import _on_job_completed

	job_data = {
		"job_id": "job-1",
		"user_id": "user_abc",
		"name": "Test Job",
		"results_s3_key": "results/job-1.json",
	}

	_on_job_completed(job_data=job_data, results_summary={"rows": 5})

	mock_docs.dispatch_job_completed.assert_not_called()
	mock_webhook.dispatch_job_completed.assert_called_once()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_job_manager_docs_dispatch.py -v`
Expected: FAIL — `_on_job_completed` does not exist in `job_manager`.

- [ ] **Step 4: Refactor job_manager to extract `_on_job_completed`**

In `backend/job_manager.py`:

a. Add import at the top with other handler imports:

```python
from docs_exporter import DocsExporter
```

b. Add a helper function near the existing `WebhookDispatcher.dispatch_job_completed` call site:

```python
def _on_job_completed(job_data: dict, results_summary: dict) -> None:
	"""Fan out post-completion notifications: webhooks + export destinations."""
	job_id = job_data["job_id"]
	user_id = job_data.get("user_id", "")
	try:
		WebhookDispatcher.dispatch_job_completed(
			job_id=job_id, user_id=user_id, job_data=job_data, results_summary=results_summary,
		)
	except Exception as e:
		logger.warning("Failed to dispatch job.completed webhook", error=str(e))

	destination_ids = job_data.get("export_destination_ids") or []
	if destination_ids:
		try:
			DocsExporter.dispatch_job_completed(
				job_id=job_id,
				user_id=user_id,
				destination_ids=destination_ids,
				results_s3_key=job_data.get("results_s3_key", ""),
				job_data=job_data,
			)
		except Exception as e:
			logger.warning("Failed to dispatch Docs export", error=str(e))
```

c. Replace the existing `WebhookDispatcher.dispatch_job_completed(...)` call site (around line 533, found in Step 1) with `_on_job_completed(job_data=..., results_summary=...)`. Keep the same arguments that were passed before.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_job_manager_docs_dispatch.py -v`
Expected: 2 passed.

- [ ] **Step 6: Allow `export_destination_ids` field in job creation**

Locate the existing job validation in `backend/utils.py` (function `validate_job_data`) or `backend/handler.py` (`create_job_handler`). Add `export_destination_ids` to the allowed optional fields and persist it on the job item.

In `backend/utils.py`, in `validate_job_data` (or wherever fields are whitelisted), add:

```python
# Optional list of destination IDs. Empty list is fine; missing key also fine.
if "export_destination_ids" in job_data:
	ids = job_data["export_destination_ids"]
	if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
		raise ValueError("export_destination_ids must be a list of strings")
	if len(ids) > 10:
		raise ValueError("Maximum 10 export destinations per job")
```

In the `create_job_handler` in `backend/handler.py`, ensure `export_destination_ids` is copied from the request body into the persisted job item alongside the other optional fields.

- [ ] **Step 7: Run full backend test suite**

Run: `cd backend && uv run pytest -v`
Expected: All existing tests pass; the 2 new ones from Step 5 pass.

- [ ] **Step 8: Deploy**

Run: `doppler run --project sf-snowscrape --config dev -- npx sst deploy --stage dev`
Expected: Stack deploys.

- [ ] **Step 9: Commit**

```bash
git add backend/job_manager.py backend/utils.py backend/handler.py backend/tests/unit/test_job_manager_docs_dispatch.py
git commit -m "feat(backend): wire export destinations into job completion fan-out"
```

---

## Phase 6: Frontend UX

### Task 12: API client + hooks

**Files:**
- Create: `frontend/lib/api/integrations.ts`
- Create: `frontend/lib/api/destinations.ts`
- Create: `frontend/lib/hooks/useGoogleAccount.ts`
- Create: `frontend/lib/hooks/useDestinations.ts`

- [ ] **Step 1: Create the Google account API client**

Create `frontend/lib/api/integrations.ts`:

```ts
import { apiFetch } from "@/lib/api/client";

export type GoogleAccount = {
  google_user_id: string;
  email: string;
  name: string;
  connected_at: string | null;
};

export async function getGoogleAuthUrl(): Promise<{ auth_url: string; state: string }> {
  return apiFetch<{ auth_url: string; state: string }>("/integrations/google/auth-url");
}

export async function completeGoogleOAuth(code: string, state: string): Promise<{ email: string; name: string }> {
  return apiFetch<{ email: string; name: string }>("/integrations/google/callback", {
    method: "POST",
    body: JSON.stringify({ code, state }),
  });
}

export async function listGoogleAccounts(): Promise<{ accounts: GoogleAccount[] }> {
  return apiFetch<{ accounts: GoogleAccount[] }>("/integrations/google");
}

export async function revokeGoogleAccount(): Promise<void> {
  await apiFetch<void>("/integrations/google", { method: "DELETE" });
}
```

- [ ] **Step 2: Create the destinations API client**

Create `frontend/lib/api/destinations.ts`:

```ts
import { apiFetch } from "@/lib/api/client";

export type DestinationMode = "new_doc_per_run" | "one_doc_per_row";
export type DestinationFormat = "structured_log" | "compact_list" | "narrative";

export type ExportDestination = {
  destination_id: string;
  user_id: string;
  name: string;
  type: "google_docs";
  drive_folder_id: string;
  naming_template: string;
  mode: DestinationMode;
  format_template: DestinationFormat;
  created_at: string;
};

export type CreateDestinationInput = Omit<ExportDestination, "destination_id" | "user_id" | "created_at">;

export async function listDestinations(): Promise<{ destinations: ExportDestination[] }> {
  return apiFetch<{ destinations: ExportDestination[] }>("/export-destinations");
}

export async function createDestination(input: CreateDestinationInput): Promise<ExportDestination> {
  return apiFetch<ExportDestination>("/export-destinations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function deleteDestination(destinationId: string): Promise<void> {
  await apiFetch<void>(`/export-destinations/${destinationId}`, { method: "DELETE" });
}
```

- [ ] **Step 3: Create TanStack Query hooks for Google account**

Create `frontend/lib/hooks/useGoogleAccount.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  completeGoogleOAuth,
  getGoogleAuthUrl,
  listGoogleAccounts,
  revokeGoogleAccount,
} from "@/lib/api/integrations";

const KEY = ["google-accounts"] as const;

export function useGoogleAccounts() {
  return useQuery({ queryKey: KEY, queryFn: listGoogleAccounts });
}

export function useStartGoogleOAuth() {
  return useMutation({ mutationFn: getGoogleAuthUrl });
}

export function useCompleteGoogleOAuth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, state }: { code: string; state: string }) => completeGoogleOAuth(code, state),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRevokeGoogleAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: revokeGoogleAccount,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
```

- [ ] **Step 4: Create TanStack Query hooks for destinations**

Create `frontend/lib/hooks/useDestinations.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDestination,
  deleteDestination,
  listDestinations,
  type CreateDestinationInput,
} from "@/lib/api/destinations";

const KEY = ["export-destinations"] as const;

export function useDestinations() {
  return useQuery({ queryKey: KEY, queryFn: listDestinations });
}

export function useCreateDestination() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateDestinationInput) => createDestination(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteDestination() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDestination(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
```

- [ ] **Step 5: Verify type-check**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: No errors related to the new files. (If `apiFetch` does not exist at `@/lib/api/client`, find the actual fetch helper in the repo and update the imports accordingly — same for `@/` path alias.)

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api/integrations.ts frontend/lib/api/destinations.ts frontend/lib/hooks/useGoogleAccount.ts frontend/lib/hooks/useDestinations.ts
git commit -m "feat(frontend): add API clients + hooks for integrations + destinations"
```

---

### Task 13: Integrations page (connect Google account)

**Files:**
- Create: `frontend/app/(application)/dashboard/integrations/page.tsx`
- Create: `frontend/app/(application)/dashboard/integrations/google/callback/page.tsx`

- [ ] **Step 1: Build the integrations index page**

Create `frontend/app/(application)/dashboard/integrations/page.tsx`:

```tsx
"use client";

import { useGoogleAccounts, useRevokeGoogleAccount, useStartGoogleOAuth } from "@/lib/hooks/useGoogleAccount";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function IntegrationsPage() {
  const { data, isLoading } = useGoogleAccounts();
  const start = useStartGoogleOAuth();
  const revoke = useRevokeGoogleAccount();
  const account = data?.accounts[0];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Integrations</h1>
        <p className="text-muted-foreground">Connect external services to export your scrape results.</p>
      </div>

      <Card className="p-6 bg-card text-card-foreground border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium">Google</h2>
            <p className="text-sm text-muted-foreground">
              Export scrape results to Google Docs in your Drive.
            </p>
          </div>

          {isLoading ? (
            <span className="text-sm text-muted-foreground">Loading…</span>
          ) : account ? (
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-sm font-medium">{account.email}</div>
                <div className="text-xs text-muted-foreground">Connected</div>
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  if (confirm(`Disconnect ${account.email}? Existing destinations will stop working.`)) {
                    revoke.mutate();
                  }
                }}
                disabled={revoke.isPending}
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <Button
              onClick={async () => {
                const r = await start.mutateAsync();
                sessionStorage.setItem("google_oauth_state", r.state);
                window.location.href = r.auth_url;
              }}
              disabled={start.isPending}
            >
              Connect Google
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Build the OAuth callback page**

Create `frontend/app/(application)/dashboard/integrations/google/callback/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCompleteGoogleOAuth } from "@/lib/hooks/useGoogleAccount";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const complete = useCompleteGoogleOAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    const errParam = params.get("error");

    if (errParam) {
      setError(errParam);
      return;
    }
    if (!code || !state) {
      setError("Missing code or state");
      return;
    }
    const expected = sessionStorage.getItem("google_oauth_state");
    if (expected !== state) {
      setError("State mismatch — possible CSRF");
      return;
    }
    sessionStorage.removeItem("google_oauth_state");

    complete.mutate(
      { code, state },
      {
        onSuccess: () => router.replace("/dashboard/integrations"),
        onError: (e: unknown) => setError(e instanceof Error ? e.message : "Connection failed"),
      },
    );
  }, [params, complete, router]);

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-destructive">Connection failed</h1>
        <p className="text-muted-foreground">{error}</p>
        <a className="underline text-primary" href="/dashboard/integrations">
          Back to Integrations
        </a>
      </div>
    );
  }

  return <div className="text-muted-foreground">Finishing connection…</div>;
}
```

- [ ] **Step 3: Add nav entry**

In `frontend/components/layout/AppSidebar.tsx`, locate the icon nav array and add an entry for Integrations. Use a `Plug` icon from `lucide-react`. Place it after "Settings" or wherever fits the existing pattern.

Example addition (adapt to the actual nav array shape in the file):

```tsx
{ icon: Plug, label: "Integrations", href: "/dashboard/integrations" },
```

Add the import: `import { Plug } from "lucide-react";`

- [ ] **Step 4: Verify type-check + lint**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm lint`
Expected: No errors.

- [ ] **Step 5: Manual smoke test**

Run: `pnpm dev` (from root) and navigate to `http://localhost:3001/dashboard/integrations`. Click "Connect Google" — should redirect to Google consent. Complete consent — should land on `/dashboard/integrations/google/callback`, then redirect back to integrations index showing the connected email.

If the redirect URI was registered in Google Cloud Console as `http://localhost:3001/dashboard/integrations/google/callback`, this works. If not, register it.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/\(application\)/dashboard/integrations/ frontend/components/layout/AppSidebar.tsx
git commit -m "feat(frontend): add Integrations page + Google OAuth callback"
```

---

### Task 14: Destinations page — list + create + delete

**Files:**
- Create: `frontend/app/(application)/dashboard/destinations/page.tsx`
- Create: `frontend/app/(application)/dashboard/destinations/new/page.tsx`
- Create: `frontend/components/destinations/DrivePicker.tsx`
- Modify: `frontend/components/layout/AppSidebar.tsx`
- Modify: `frontend/next.config.mjs`

- [ ] **Step 1: Allow Google Picker SDK script in CSP / image domains**

In `frontend/next.config.mjs`, ensure scripts from `https://apis.google.com` and `https://docs.google.com` are allowed if a Content-Security-Policy is configured. If no CSP is set, no change required.

- [ ] **Step 2: Build the Drive Picker component**

Create `frontend/components/destinations/DrivePicker.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import { Button } from "@/components/ui/button";

declare global {
  interface Window {
    gapi?: any;
    google?: any;
  }
}

type Props = {
  onSelect: (folderId: string, folderName: string) => void;
  accessToken: string;
};

export function DrivePicker({ onSelect, accessToken }: Props) {
  const [ready, setReady] = useState(false);
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_API_KEY;
  const appId = process.env.NEXT_PUBLIC_GOOGLE_PROJECT_NUMBER;

  useEffect(() => {
    if (!window.gapi) return;
    window.gapi.load("picker", () => setReady(true));
  }, []);

  function open() {
    if (!ready || !window.google?.picker) return;
    const view = new window.google.picker.DocsView(window.google.picker.ViewId.FOLDERS)
      .setIncludeFolders(true)
      .setSelectFolderEnabled(true)
      .setMimeTypes("application/vnd.google-apps.folder");
    const picker = new window.google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setDeveloperKey(apiKey ?? "")
      .setAppId(appId ?? "")
      .setCallback((data: any) => {
        if (data.action === window.google.picker.Action.PICKED) {
          const doc = data.docs[0];
          onSelect(doc.id, doc.name);
        }
      })
      .build();
    picker.setVisible(true);
  }

  return (
    <>
      <Script src="https://apis.google.com/js/api.js" strategy="afterInteractive" />
      <Button type="button" variant="outline" onClick={open} disabled={!ready}>
        {ready ? "Pick Drive folder" : "Loading picker…"}
      </Button>
    </>
  );
}
```

Note: `NEXT_PUBLIC_GOOGLE_API_KEY` and `NEXT_PUBLIC_GOOGLE_PROJECT_NUMBER` must be set in `frontend/.env.local`. The API key is a public Google Cloud API key restricted to the Picker API; the project number is the numeric project ID from Google Cloud Console.

- [ ] **Step 3: Build the destinations index page**

Create `frontend/app/(application)/dashboard/destinations/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useDeleteDestination, useDestinations } from "@/lib/hooks/useDestinations";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function DestinationsPage() {
  const { data, isLoading } = useDestinations();
  const del = useDeleteDestination();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Export Destinations</h1>
          <p className="text-muted-foreground">
            Send job results to Google Docs in your Drive.
          </p>
        </div>
        <Link href="/dashboard/destinations/new">
          <Button>New Destination</Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading…</div>
      ) : !data?.destinations.length ? (
        <Card className="p-6 bg-card text-card-foreground border-border">
          <p className="text-muted-foreground">
            No destinations yet. Connect a Google account and create one.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {data.destinations.map((d) => (
            <Card key={d.destination_id} className="p-4 bg-card text-card-foreground border-border">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{d.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {d.format_template} · {d.mode}
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (confirm(`Delete destination "${d.name}"?`)) del.mutate(d.destination_id);
                  }}
                  disabled={del.isPending}
                >
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Build the destination create form**

Create `frontend/app/(application)/dashboard/destinations/new/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { useCreateDestination } from "@/lib/hooks/useDestinations";
import { useGoogleAccounts } from "@/lib/hooks/useGoogleAccount";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const schema = z.object({
  name: z.string().min(1).max(100),
  drive_folder_id: z.string().min(1, "Pick a Drive folder"),
  naming_template: z.string().min(1).max(200),
  mode: z.enum(["new_doc_per_run", "one_doc_per_row"]),
  format_template: z.enum(["structured_log", "compact_list", "narrative"]),
});

type FormValues = z.infer<typeof schema>;

export default function NewDestinationPage() {
  const router = useRouter();
  const create = useCreateDestination();
  const { data: accountsData, isLoading: accountsLoading } = useGoogleAccounts();
  const hasAccount = !!accountsData?.accounts.length;

  const { register, handleSubmit, setValue, watch, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: "new_doc_per_run",
      format_template: "structured_log",
      naming_template: "{{job_name}} — {{date}}",
    },
  });

  const folderId = watch("drive_folder_id");

  async function onSubmit(values: FormValues) {
    await create.mutateAsync({ ...values, type: "google_docs" });
    router.push("/dashboard/destinations");
  }

  if (accountsLoading) return <div className="text-muted-foreground">Loading…</div>;
  if (!hasAccount) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold">No Google account connected</h1>
        <p className="text-muted-foreground">
          Connect one from{" "}
          <a className="text-primary underline" href="/dashboard/integrations">Integrations</a>.
        </p>
      </div>
    );
  }

  return (
    <Card className="p-6 max-w-2xl bg-card text-card-foreground border-border">
      <h1 className="text-2xl font-semibold text-foreground mb-4">New Destination</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" {...register("name")} />
          {formState.errors.name && <p className="text-sm text-destructive">{formState.errors.name.message}</p>}
        </div>

        <div className="space-y-2">
          <Label>Drive folder</Label>
          <div className="flex gap-2 items-center">
            <Input
              readOnly
              value={folderId || "No folder selected"}
              className="flex-1"
            />
            <Input
              {...register("drive_folder_id")}
              placeholder="Or paste folder ID"
              onChange={(e) => setValue("drive_folder_id", e.target.value)}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Paste a Google Drive folder ID for now. (Picker UI ships in v1.1.)
          </p>
          {formState.errors.drive_folder_id && (
            <p className="text-sm text-destructive">{formState.errors.drive_folder_id.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="naming_template">Doc name template</Label>
          <Input id="naming_template" {...register("naming_template")} />
          <p className="text-xs text-muted-foreground">
            Variables: {`{{job_name}}, {{date}}`}
          </p>
        </div>

        <div className="space-y-2">
          <Label>Mode</Label>
          <Select
            value={watch("mode")}
            onValueChange={(v) => setValue("mode", v as FormValues["mode"])}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="new_doc_per_run">New doc per run</SelectItem>
              <SelectItem value="one_doc_per_row">One doc per row</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Format</Label>
          <Select
            value={watch("format_template")}
            onValueChange={(v) => setValue("format_template", v as FormValues["format_template"])}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="structured_log">Structured log</SelectItem>
              <SelectItem value="compact_list">Compact list</SelectItem>
              <SelectItem value="narrative">Narrative</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2 pt-2">
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create destination"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
```

(Note: the actual Drive Picker integration is deferred to v1.1 here to keep the create form simple; users paste folder IDs in v1.0. The `DrivePicker` component built in Step 2 is left in the codebase ready to wire in. Update the form layout to insert `<DrivePicker accessToken={...} onSelect={...} />` once you have the access-token-fetching endpoint ready.)

- [ ] **Step 5: Add Destinations nav entry**

In `frontend/components/layout/AppSidebar.tsx`, add a nav entry for Destinations near the Integrations one:

```tsx
{ icon: Send, label: "Destinations", href: "/dashboard/destinations" },
```

Add the import: `import { Send } from "lucide-react";`

- [ ] **Step 6: Verify type-check + lint**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm lint`
Expected: No errors.

- [ ] **Step 7: Manual smoke test**

Run: `pnpm dev` from root. Navigate to `/dashboard/destinations`, create one with a real Drive folder ID. Verify it appears in the list and can be deleted.

- [ ] **Step 8: Commit**

```bash
git add frontend/app/\(application\)/dashboard/destinations/ frontend/components/destinations/DrivePicker.tsx frontend/components/layout/AppSidebar.tsx
git commit -m "feat(frontend): add Export Destinations CRUD UI"
```

---

### Task 15: Job creation — attach destinations

**Files:**
- Create: `frontend/components/destinations/DestinationSelector.tsx`
- Modify: `frontend/app/(application)/dashboard/jobs/new/page.tsx`

- [ ] **Step 1: Build the selector component**

Create `frontend/components/destinations/DestinationSelector.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useDestinations } from "@/lib/hooks/useDestinations";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

type Props = {
  value: string[];
  onChange: (ids: string[]) => void;
};

export function DestinationSelector({ value, onChange }: Props) {
  const { data, isLoading } = useDestinations();

  function toggle(id: string, checked: boolean) {
    onChange(checked ? [...value, id] : value.filter((x) => x !== id));
  }

  if (isLoading) return <div className="text-muted-foreground">Loading…</div>;
  if (!data?.destinations.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No destinations yet.{" "}
        <Link className="text-primary underline" href="/dashboard/destinations/new">
          Create one
        </Link>
        .
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {data.destinations.map((d) => (
        <div key={d.destination_id} className="flex items-center gap-2">
          <Checkbox
            id={`dest-${d.destination_id}`}
            checked={value.includes(d.destination_id)}
            onCheckedChange={(c) => toggle(d.destination_id, Boolean(c))}
          />
          <Label htmlFor={`dest-${d.destination_id}`} className="font-normal">
            {d.name}
            <span className="text-xs text-muted-foreground ml-2">
              ({d.format_template} · {d.mode})
            </span>
          </Label>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Wire into the job creation form**

In `frontend/app/(application)/dashboard/jobs/new/page.tsx`, add the selector to the form. Locate the form's state object (look for a `useForm` or `useState` block managing job fields). Add a `export_destination_ids: string[]` field with default `[]`.

In the JSX, before the submit button row, add a section like:

```tsx
<section className="space-y-2">
  <Label>Send results to</Label>
  <p className="text-sm text-muted-foreground">
    Pick destinations to receive results when this job completes.
  </p>
  <DestinationSelector
    value={form.watch("export_destination_ids") ?? []}
    onChange={(ids) => form.setValue("export_destination_ids", ids)}
  />
</section>
```

Add the import: `import { DestinationSelector } from "@/components/destinations/DestinationSelector";`

If the form uses Zod, extend the schema:

```ts
export_destination_ids: z.array(z.string()).max(10).default([]),
```

Ensure `export_destination_ids` is included in the request body sent to `POST /jobs`.

- [ ] **Step 3: Verify type-check + lint**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm lint`
Expected: No errors.

- [ ] **Step 4: Manual smoke test**

Run: `pnpm dev`. Navigate to `/dashboard/jobs/new`. Verify the "Send results to" section appears with the existing destinations. Create a job with a destination selected.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/destinations/DestinationSelector.tsx frontend/app/\(application\)/dashboard/jobs/new/page.tsx
git commit -m "feat(frontend): attach export destinations to jobs at creation"
```

---

### Task 16: End-to-end test

**Files:**
- Create: `frontend/e2e/google-docs-destination.spec.ts`

- [ ] **Step 1: Write the e2e spec**

Create `frontend/e2e/google-docs-destination.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test.describe("Google Docs destination", () => {
  test("user can view Destinations page when none exist", async ({ page }) => {
    await page.goto("/dashboard/destinations");
    await expect(page.getByText(/no destinations yet/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /new destination/i })).toBeVisible();
  });

  test("create form blocks submission until a folder is provided", async ({ page }) => {
    await page.goto("/dashboard/destinations/new");
    const submit = page.getByRole("button", { name: /create destination/i });
    await page.getByLabel("Name").fill("Test Destination");
    await submit.click();
    await expect(page.getByText(/pick a drive folder/i)).toBeVisible();
  });

  test("Integrations page shows Connect Google button when not connected", async ({ page }) => {
    await page.goto("/dashboard/integrations");
    await expect(page.getByRole("button", { name: /connect google/i })).toBeVisible();
  });
});
```

(Note: This e2e suite covers UI surfaces deterministically without hitting Google's real OAuth. A full happy-path test that mocks the Google API would live in the backend integration suite — already covered in Task 10.)

- [ ] **Step 2: Run e2e**

Run: `cd frontend && pnpm test:e2e google-docs-destination.spec.ts`
Expected: 3 passed. (Requires the dev server to be running, or Playwright's auto-start config.)

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/google-docs-destination.spec.ts
git commit -m "test(frontend): e2e for Google Docs destination UI surfaces"
```

---

## Phase 7: Documentation

### Task 17: Update infrastructure docs

**Files:**
- Modify: `docs/INFRASTRUCTURE.md`

- [ ] **Step 1: Append change log entry**

In `docs/INFRASTRUCTURE.md`, locate the Change Log section and add:

```
- 2026-06-01: Added Google Docs export destination feature. New AWS resources:
  KMS key (alias/snowscrape-{stage}-oauth-tokens), 3 DynamoDB tables
  (GoogleAccounts, ExportDestinations, DocsExports), SQS queue+DLQ
  (DocsExportQueue, DocsExportDLQ), and SQS-subscriber Lambda. New env vars:
  GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REDIRECT_URI
  (from Doppler), OAUTH_TOKEN_KMS_KEY_ID (from SST). New routes:
  /integrations/google/{auth-url,callback,(list),(delete)} and
  /export-destinations/{POST,GET,DELETE}. — Alex Diaz
```

- [ ] **Step 2: Update "Last Updated" header**

In `docs/INFRASTRUCTURE.md`, update the document header date to `2026-06-01`.

- [ ] **Step 3: Add a "Google Docs Export" subsection**

Under the "Third-party services" or equivalent section, add:

```
### Google Docs Export

- **OAuth scopes**: drive.file (create-only), drive.metadata.readonly (folder
  metadata for picker), documents (write to Docs), openid/email/profile.
- **Token storage**: refresh tokens KMS-encrypted (alias/snowscrape-{stage}-oauth-tokens)
  before persisting to GoogleAccounts DynamoDB table. Access tokens are not stored.
- **Delivery**: post-job-completion fan-out via DocsExportQueue (SQS, 3 retries +
  DLQ). Triggered alongside webhook delivery in job_manager._on_job_completed.
- **Billing**: not metered against plan limits in v1.0.
```

- [ ] **Step 4: Update PROGRESS.md**

In the repo root, locate `PROGRESS.md`. Under the appropriate "Recently completed" or "In progress" section, add:

```
- Google Docs export destination — connect Google account, create reusable
  destinations, results auto-exported to Drive after each job run.
```

- [ ] **Step 5: Update master TODO**

In `C:\Users\alexi\.claude\TODO.md`, if there was a tracked item for "Google Docs export" or similar, mark it complete. Otherwise add a brief note that this feature shipped on 2026-06-01.

- [ ] **Step 6: Commit**

```bash
git add docs/INFRASTRUCTURE.md PROGRESS.md
git commit -m "docs: document Google Docs export feature (infra + progress)"
```

---

## Phase 8: Production deploy

### Task 18: Deploy to prod

**Files:**
- None (deploy-only)

- [ ] **Step 1: Promote Doppler secrets to prod config**

Run: `doppler secrets set GOOGLE_OAUTH_CLIENT_ID=... --project sf-snowscrape --config prod` (and likewise for `GOOGLE_OAUTH_CLIENT_SECRET` and `GOOGLE_OAUTH_REDIRECT_URI=https://scrape.snowforge.dev/dashboard/integrations/google/callback`)
Expected: Each command echoes the key with a redacted preview.

- [ ] **Step 2: Register prod redirect URI in Google Cloud Console**

In Google Cloud Console → OAuth 2.0 Client → Authorized redirect URIs, add `https://scrape.snowforge.dev/dashboard/integrations/google/callback`.

- [ ] **Step 3: Deploy backend to prod**

Run: `doppler run --project sf-snowscrape --config prod -- npx sst deploy --stage prod`
Expected: Stack deploys; new tables, queue, Lambda, and routes appear in the output.

- [ ] **Step 4: Deploy frontend**

The Vercel-linked frontend auto-deploys on push to `main`. Confirm the deployment in Vercel shows the new pages and that env vars `NEXT_PUBLIC_GOOGLE_API_KEY` and `NEXT_PUBLIC_GOOGLE_PROJECT_NUMBER` are set on the prod environment.

Run: `cd frontend && pnpm vercel env ls production` (if Vercel CLI is installed; otherwise check the dashboard)
Expected: Both keys present in production.

- [ ] **Step 5: Smoke test in prod**

Log into `https://scrape.snowforge.dev`, navigate to Integrations, connect a Google test account, create a destination targeting a test folder in that account's Drive, run a small job with the destination attached, verify the Doc appears in Drive within ~30 seconds.

- [ ] **Step 6: Tag the release**

```bash
git tag -a v0.X.0-docs-export -m "Google Docs export destination GA"
git push origin v0.X.0-docs-export
```

(Replace `v0.X.0` with whatever follows your latest tag — check `git describe --tags --abbrev=0` if unsure.)

---

## Notes on deferred work

The following intentionally do not appear as tasks. Add follow-up tickets if the user-flow exposes them as needs:

- **Drive Picker SDK fully wired into the create form**: the `DrivePicker` component is built in Task 14 Step 2 but not yet inserted into `NewDestinationPage` because it depends on having an access token available to the frontend. Backend endpoint `/integrations/google/access-token` would be needed (and is a v1.1 concern). For v1.0 users paste folder IDs.
- **Google Sheets**: same OAuth, same destination row shape with `type: "google_sheets"`. Add a new formatter (`sheets_formatter.py`) and branch in `docs_export_handler._process_one` on `dest["type"]`.
- **Append mode** (`append_to_existing`): requires resolving the previous doc ID from a prior `DocsExports` row and using `insertText` at end-of-doc rather than create.
- **Org sharing**: `org_id` GSI + permission check; defer until multi-user orgs are a thing.
- **Billing meter**: add `docs_exports_count` to subscription limits, enforce in `_on_job_completed` via `billing.check_usage`.
- **OAuth token rotation alarm**: alert when refresh fails repeatedly for a user (token revoked from their side).
