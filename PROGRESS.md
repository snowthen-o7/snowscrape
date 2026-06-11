# SnowScrape -- Progress & Launch Readiness

**Last Updated:** 2026-06-10
**Launch Readiness:** ~98% (live; Google Docs destination backend complete, awaiting Alex's Google Cloud OAuth client + deploy)
**Build Status:** PASSES (backend unit suite 485 passed green as of 2026-06-10, full suite 510; frontend lint 0 errors + vitest 121/121 + prod build green on claude-main as of 2026-06-10)
**Test Coverage:** ~60-70% (unit + integration; Playwright setup present)

### Recent -- 2026-06-10
- Test coverage for the previously-untested job-config validators (claude-main, PR pending; no source change). `backend/validators.py` (895 loc, the input-validation layer on the live job-create path) had a dedicated security suite (`test_security.py`: SSRF, XPath whitelist, ReDoS, job-name/url-list bounds, `validate_job_data_strict`), but five `InputValidator` methods had ZERO direct coverage: `validate_jsonpath_query`, `validate_file_mapping`, `sanitize_string`, `validate_url_template`, and `validate_source_type`. These gate real job configs (jsonpath query type, CSV column mapping, scheduled/`direct_url` templated targets, generic string scrub), so a silent behavior change would have passed CI. Added `backend/tests/unit/test_validators_input.py` (60 pure/deterministic characterization tests) pinning each method's contract: jsonpath `$`/`@` rooting + balanced-bracket + length guards; file-mapping required-key, delimiter/enclosure/escape whitelists and url_column int-range (0-100) / named-column / wrong-type rules; sanitize_string control-char stripping (newlines/tabs preserved), trim, and optional max_length; url_template empty/length/non-http-scheme/malformed-variable rejection plus plain and templated acceptance; source_type `csv`/`direct_url` allowlist. No source change (regression hardening); every method behaved exactly as written (all green on first run). An independent diff-only adversarial review (fresh code-reviewer subagent) returned APPROVE with no HIGH/MEDIUM correctness defects; its MEDIUM coverage-gap notes were addressed by adding 5 more pins for the classic Python gotchas it flagged (bool-is-int url_column accepted as an index, falsy max_length=0 disabling the length check, \r stripping, and the url_template no-hostname + unknown-variable branches). Evidence: new file 65 passed; full backend suite 510 passed / 0 failed (was 445; +65), unit-only 485 (was 420).
- Dropped Parquet as an offered export format (claude-main, PR pending, closes #33 on merge to main). The JobCard download menu offered Parquet, but Parquet needs `pyarrow`, which is intentionally NOT bundled in the Lambda (size / cold-start cost, decided in the #32 rewrite), so every Parquet download failed 100% of the time in prod. Issue #33 framed this as "bundle pyarrow vs drop the format"; since the no-bundle decision is already made, dropping it is the logical consequence, not a new product call. Changes: extracted the offered set into a pure, testable `frontend/lib/jobs/exportFormats.ts` (`EXPORT_FORMATS` = json/csv/xlsx/sql, with an `ExportFormat` type) and wired `JobCard` to it; tightened the `jobsAPI.download` format union to drop `'parquet'`; removed `'parquet'` from the backend download handler's `valid_formats` so a Parquet request now returns a clean 400 ("Invalid format") instead of reaching the converter's handled RuntimeError -> 500; and scrubbed Parquet from every user-facing surface that advertised it as available (home, features, getting-started, exporting-data docs incl. the dedicated card + comparison-table row, docs/api/jobs, `docs/API.md`, `backend/openapi.yml` both enums + description, README). `convert_to_parquet` stays in `format_converter.py` as dormant code (and keeps its handled-error test), so re-enabling later is just bundling pyarrow + re-adding 'parquet' to `EXPORT_FORMATS` and `valid_formats`. TDD: new `frontend/lib/__tests__/jobs/exportFormats.test.ts` (3 tests: exact offered set, Parquet excluded, every format has a label+description). Evidence: frontend vitest 121 passed / 0 failed (was 118; +3); backend unit suite 420 passed / 0 failed (the existing pyarrow-missing converter test still green); `eslint .` 0 errors / 106 baseline warnings; `doppler --config dev -- pnpm build` exit 0 (Compiled successfully in 8.8s, 27/27 static pages). Backend behavior change reaches prod only on the next backend deploy (Alex-only), but the UI/marketing fix ships with the frontend; until the backend redeploys, a direct API Parquet request still hits the old 500 path rather than the new 400, which is a strict improvement either way (no longer offered in the UI).
- Spreadsheet formula-injection hardening for CSV/XLSX exports (claude-main, PR pending, closes #34 on merge to main). Export cells are arbitrary scraped (attacker-influenced) web content; `backend/format_converter.py` wrote them verbatim, so a value beginning with `=`, `+`, `-`, `@`, tab, or CR (e.g. `=HYPERLINK("http://evil","click")`) is evaluated as a formula when the export is opened in Excel / Google Sheets / LibreOffice (CSV/spreadsheet formula injection, CWE-1236). Pre-existing (the old pandas converter had the same gap; surfaced during the #32 rewrite). Fix: new `_sanitize_spreadsheet_text` helper prefixes a single quote when the stringified value starts with a trigger char, applied to the CSV write path and to string-valued XLSX cells (numbers/bools stay native so they remain numeric in Excel; openpyxl would otherwise store a leading-`=` string as a real formula cell). The header row is sanitized too (column names come from scraped/AI-derived JSON keys). SQL and Parquet are intentionally untouched: SQL emits single-quote-escaped string literals (not formula-evaluated) and Parquet is a binary data format. TDD: 12 new tests in `backend/tests/unit/test_format_converter.py` (parametrized CSV payloads incl. `=`/`+`/`-`/`@`/tab/CR, benign-values-unchanged, XLSX formula cell `data_type != 'f'` with native numbers preserved, CSV+XLSX header sanitization, and a scope guard that SQL output is NOT spreadsheet-quoted). Independent diff-only adversarial review (fresh code-reviewer subagent) flagged one HIGH (the header row was initially unsanitized); fixed before merge, plus added the header regression + SQL scope-lock tests it requested. Evidence: full backend suite 445 passed / 0 failed (was 433; +12). Reaches prod on the next backend deploy (Alex-only), same deploy as the #32 pandas-free converter.
- Multi-format export made pandas-free so non-JSON downloads stop crashing in prod (claude-main, PR pending, closes #32 on merge to main). `backend/format_converter.py` imported `pandas` and `openpyxl` at module top, but pandas is intentionally NOT bundled in the Lambda (same fact behind the 2026-06-08 CSV-parsing fix), and the download handler imported the converter and called `prepare_dataframe()` OUTSIDE its conversion `try/except`. So the first non-JSON download of an uncached job raised an unhandled `ModuleNotFoundError`: CSV, XLSX, Parquet, and SQL exports were all broken in prod (only JSON worked), despite "Multi-Format Export" reading Complete. Fix: rewrote the converters pandas-free. CSV (stdlib `csv.DictWriter`) and SQL (manual writer) now work with zero heavy deps and are directly testable; XLSX uses `openpyxl` (a pure-Python wheel, added to `backend/pyproject.toml` so it bundles); Parquet still needs `pyarrow` (too large to bundle), so it raises a clear, handled `RuntimeError` instead of crashing. `prepare_dataframe` now builds rows + a first-seen column union (matching the old `pd.DataFrame(list_of_dicts)` ordering) and the module resolves S3 lazily via `connection_pool.get_s3_client()` (the old module-level `boto3.client('s3')` pinned credentials at import and broke under moto). Also moved the converter import + `prepare_dataframe()` inside the handler's conversion guard so any failure returns a clean 500. SQL identifiers are now backtick-escaped (scraped JSON keys are untrusted) and empty results emit a SQL comment instead of invalid `CREATE TABLE ... ()`. TDD: new `backend/tests/unit/test_format_converter.py` (14 tests: CSV/SQL/XLSX round-trips via moto, prepare flatten/non-flatten column union, None->''/NULL, list/dict scalarization, batch-of-100, backtick-escaping, empty-results, the pyarrow-missing RuntimeError path, and a no-pandas import guard). Independent diff-only adversarial review (fresh code-reviewer subagent) APPROVE, no HIGH; its two MEDIUMs (backtick identifier injection + invalid empty-table DDL) both fixed before merge. Evidence: full backend suite 433 passed / 0 failed (was 419; +14); pandas + pyarrow confirmed absent in the env (matches prod), openpyxl present. NOTE: the openpyxl dep + the pandas-free converters reach prod only on a backend deploy (Alex-only); until then prod still 500s on non-JSON downloads.
- Test coverage for the URL-variable resolver (claude-main, PR pending). `backend/url_variable_resolver.py` (429 loc, the PHP-style `{{date}}`/`{{time}}` templating that expands scheduled-scraping `url_template`s) had ZERO dedicated tests, despite being on the live job-create/run path (`utils.resolve_url_template`/`preview_url_template` and `validators.JobValidator.validate_timezone` both call into it). Added `backend/tests/unit/test_url_variable_resolver.py` (53 tests, pure/deterministic against a fixed `exec_time`) pinning every documented behavior: default + custom PHP formats (`Y-m-d`, `m/d/Y`, `Y-m-d_h_iA`, 2-digit year), time offsets (`+1d`/`-1d`/`+2h`/`-30m`/`+15s`, day rollover), no-leading-zero specifiers (`n`/`j`/`G`/`g`) vs padded (`m`/`d`/`H`/`h`), lowercase vs uppercase meridiem (`a`/`A`), the 12-hour midnight/noon wrap (00->12 AM, 12->12 PM), timezone resolution (UTC->America/New_York shifts the hour and can roll the date back) with graceful fall-back to UTC on an invalid tz, `has_variables`/`extract_variables`, `validate_template` (empty, unmatched braces, bad variable name, literal-passthrough format chars) and `validate_timezone`, the defensive-copy contract of `get_common_timezones`, and the full `preview()` payload (valid, invalid-template, invalid-timezone, and tz-reflected `resolved`/`resolved_at`). No source change (characterization/regression hardening); the module behaved exactly as documented (all 53 green on first run). Evidence: new file 53 passed in 2.12s; full backend suite 419 passed / 0 failed (was 366; +53).
- openapi.yml `servers` now point at the real API Gateway hosts (claude-main, PR pending, closes #24 on merge to main). The published spec (referenced from `docs/API.md`, the programmatic-API launch surface) shipped an unusable `servers` block: a `localhost:3000` entry (misleading, the backend is only reachable via API Gateway, and the dev server binds 3001 anyway) and a templated `https://{apiId}.execute-api.us-east-2.amazonaws.com/{stage}` whose `apiId` defaulted to `REPLACE_ME`, so SDK generators and Swagger UI "Try it out" resolved to a dead host. Fix (docs/spec-only, no runtime change): replaced the block with two concrete bare-host servers, Production `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com` (listed first, the default) and Development `https://g5vmashyda.execute-api.us-east-2.amazonaws.com`. These are HTTP API (V2) gateways on the auto `$default` stage (`sst.config.ts` `ApiGatewayV2`, routes registered as `POST /jobs` etc.), so routes are served at the host root with NO stage path prefix; the URLs match `frontend/.env.example` `NEXT_PUBLIC_API_BASE_URL` (the working client) and `docs/INFRASTRUCTURE.md`. Also corrected `docs/API.md`, whose base-URL example wrongly carried a `/prod` suffix (inconsistent with its own `$BASE_URL/jobs` curl examples). Extended the `test_openapi_spec.py` drift guard with three tests: no `REPLACE_ME`/placeholder in any server URL or variable default; servers resolve to the real prod gateway and include no localhost host; and no server URL carries a stage path segment (root-served V2 API). Deferred (issue #24 point 3, larger): emit the server URLs from SST stack outputs so they cannot drift per redeploy. Self-review caught the initial draft's incorrect `/prod`//`dev` suffixes before merge. Evidence: full backend suite 366 passed / 0 failed (was 363; +3 server-block guard tests). Frontend untouched.

### Recent -- 2026-06-08
- Pinned all frontend dependencies + enforced a frozen lockfile in CI (claude-main, PR pending, closes #17 on merge to main). `frontend/package.json` declared ~50 deps as `"latest"` while the Frontend CI workflow installed with `pnpm install --no-frozen-lockfile`, so every CI run re-resolved to whatever was newest and "passes locally" no longer implied "passes in CI". This already broke a build once (`@vitejs/plugin-react: latest` resolved to 6.0.1, which needs Vite 8 and crashed against the Vite 7.3.1 that Vitest 4 bundles). Fix (config-only, no app code): replaced every `"latest"` specifier with a caret range pinned to the exact version currently resolved (e.g. `next ^16.2.7`, `vitest ^4.1.8`, `@clerk/nextjs ^7.4.3`), keeping the already-pinned `@vitejs/plugin-react ^5.1.4` / `eslint ^9` and the `@snowforge/ui` git ref untouched; regenerated `pnpm-lock.yaml` (direct-dependency versions unchanged, verified via `pnpm ls`; some transitive deps re-resolved within their existing ranges); and switched all 4 `frontend.yml` install steps from `--no-frozen-lockfile` to `--frozen-lockfile` (matching `backend.yml`). Evidence: `pnpm install --frozen-lockfile` succeeds against the new manifest (the exact CI check), `eslint .` 0 errors / 106 baseline warnings, frontend vitest 118/118, `doppler --config dev -- pnpm build` exit 0 (Compiled successfully in 10.7s). No runtime or behavior change; upgrades are now intentional (caret within major) instead of silent.
- CSV parse errors now surface instead of being masked (claude-main, PR pending, closes #12 on merge to main). `backend/utils.py` `parse_links_from_file` wrapped the pandas path in a bare `except Exception` that unconditionally fell through to the manual `csv.reader` parser and logged only a WARNING. Because pandas is intentionally not bundled in the Lambda, the pandas branch ALWAYS raised `ImportError` in production, so the manual parser was the only path that ever ran, yet every CSV job logged a misleading "Pandas failed to parse file" WARNING and a genuine manual-parser bug looked identical to that benign warning (this is how the header-row/empty-cell ingestion bug, fixed 2026-06-06, stayed hidden). Fix (backend-only, no runtime behavior change for valid inputs): split the two parsers into `_parse_links_with_pandas` (best-effort, dev/local only) and `_parse_links_manual` (the real production path); `parse_links_from_file` now runs pandas only when `PANDAS_AVAILABLE` and treats its failure as a benign DEBUG fallback, while a failure in the manual parser is logged at ERROR and re-raised so it is never swallowed. A fetch failure now propagates directly instead of triggering an `UnboundLocalError` in the old fallback. Evidence: backend full suite 363 passed / 0 failed (338 unit incl. +3 new error-surfacing tests, 25 integration); pandas confirmed absent in the env (matches prod). Independent diff-only adversarial review APPROVE, no HIGH/MEDIUM; its one LOW (cover the pandas-available-but-fails DEBUG-downgrade path) addressed before merge with a 3rd test.
- DestinationSelector now enforces the 10-destination cap client-side (claude-main, PR #28, closes #9 on merge to main). The backend caps a job at 10 export destinations (`backend/utils.py`: "Maximum 10 export destinations per job"), but `DestinationSelector` let users check unlimited boxes, so the limit was only discovered when job creation failed with a 422. Fix (frontend-only, no runtime/backend change): a `MAX_DESTINATIONS = 10` constant (mirrors and comments the backend cap), unchecked checkboxes disabled once 10 are selected (`cursor-not-allowed opacity-50`) while already-selected boxes stay enabled so they can be unchecked, a `toggle()` guard that refuses to add beyond the cap even if a disabled control fires, and an `N / 10 selected` count plus an `aria-live` "Maximum 10 destinations per job" message at the cap. Improves all three job-creation flows (manual, AI, Visual) that share this selector. Evidence: frontend vitest 118 passed (was 113; +5 cap tests), `eslint .` 0 errors / 106 baseline warnings, `doppler --config dev -- pnpm build` exit 0 (Compiled successfully). Independent diff-only review APPROVE, no HIGH/MEDIUM (its one actionable LOW, aria-live on the cap message, addressed before merge).

### Recent -- 2026-06-07
- CSS-to-XPath translation for Visual/AI builder fields (claude-main, closes #26 on merge to main). The Visual and AI job builders relabeled a `css` field's `type` to `xpath` while leaving the query string in CSS syntax, so the backend XPath engine (`crawl_manager.py` runs only xpath/regex/jsonpath) evaluated a CSS-syntax expression and silently extracted nothing. Fix: new pure `frontend/lib/jobs/cssToXpath.ts` `cssSelectorToXPath()` that translates the common, unambiguous CSS subset (type/`*`, `#id`, `.class`, attribute selectors `[a]`/`[a=v]`/`^=`/`$=`/`*=`/`~=`/`|=`, descendant and child combinators, selector lists) to XPath 1.0 and returns `null` for anything it cannot prove correct (sibling combinators, pseudo-classes, CSS escapes, single-quoted values). Both builders now emit the translated XPath for a `css` field; if translation returns `null`, they throw a clear, field-named error that the existing job-create try/catch surfaces as a toast, so a bad selector fails loudly instead of silently losing data. AI builder's `useAi` (natural-language) path is unchanged and takes precedence. Evidence: frontend vitest 101 passed (was 51; +42 converter tests + builder translate/throw tests), `eslint .` 0 errors / 106 baseline warnings, `doppler --config dev -- pnpm build` exit 0 (Compiled successfully). No backend change; no runtime change for already-xpath auto-extracted fields.
- Visual builder job creation fixed (claude-main, PR #25, closes #8 on merge to main). The Visual Scraper Builder's "Create Job" sent a payload with no `source_type`/`url_template`, so the backend defaulted `source_type` to `'csv'` (`validators.py`) and then rejected the job for a missing `file_mapping` the flow never provides. The builder's primary action always failed validation. Fix: extracted `frontend/lib/jobs/buildVisualJobPayload.ts` (a pure helper mirroring `buildAiJobPayload`) that builds a `direct_url` `CreateJobDTO` with `url_template` set to the target URL, and downgrades `css` field types to `xpath` (the backend job runner accepts `xpath/regex/jsonpath/pdf_*`, not raw `css`). Wired into `visual/page.tsx` `handleSaveAsJob`; added 5 unit tests. Evidence: frontend vitest 56 passed (was 51), `eslint .` 0 errors, `doppler --config dev -- pnpm build` exit 0 (27/27 static pages), PR #25 Vercel preview PASS. Independent diff-only review APPROVE (no HIGH; one MEDIUM test-name fix addressed). Known follow-up (separate issue): a downgraded css field keeps its css-syntax query string labeled `xpath`, so a manually-added css field can extract nothing at runtime (auto-extracted fields are already xpath, so this is rare).
- Programmatic API: documented and spec-pinned the API-key auth that shipped on 2026-06-06 (claude/snowscrape/openapi-apikey-auth-docs, PR into claude-main). The `/jobs` data-plane accepts an `sk_live_...` API key OR a Clerk JWT (via `resolve_user_id`), but `backend/openapi.yml` still said "All endpoints require a valid Clerk JWT" and defined only the `BearerAuth` scheme, so the launch feature (sub-project #2, programmatic access) was undocumented. Changes: (1) rewrote the `info` Authentication section to describe both credential types and which surface accepts each; (2) added an `ApiKeyAuth` security scheme; (3) added `security: [BearerAuth, ApiKeyAuth]` to the 13 data-plane operations (createJob, getAllJobStatuses, getJobDetails, updateJob, deleteJob, pause/resume/cancel/refreshJob, getJobCrawls, getCrawlDetails, downloadResults, previewResults), leaving the control-plane Clerk-only by design; (4) wrote `docs/API.md`, a programmatic quickstart (create key, authenticate, job lifecycle, download, actions, rate limits); (5) added `backend/tests/unit/test_openapi_spec.py`, a drift guard that pins the spec to the real auth model (data-plane ops advertise ApiKeyAuth; control-plane ops do not), plus `pyyaml` as a dev dep. Evidence: full backend suite 360 passed / 0 failed (was 337; +23 from the new guard). No runtime code changed; frontend untouched.

### Recent -- 2026-06-06
- Backend CI red-signal fix (claude-main, pending Alex's merge to main). The `claude-main -> main` PR (#7) `Backend Tests` job failed on `test_delete_job_handler_success` with `NoCredentialsError` (issue #16). Root cause: `utils.py` bound `s3`, `job_table` and `url_table` to connection-pool resources at module IMPORT time, pinning each resource to whatever credentials resolved during import. On CI there are no ambient AWS credentials at import (moto/test creds are set up per-test, after import), so `delete_job_links -> url_table.query` reached real boto3 with no creds. It passed locally only because the dev machine has ambient creds; the import-time binding also defeated the per-test connection-pool reset in conftest. Fix: fetch the URLs table and S3 client lazily at call time via `get_table`/`get_s3_client` (the pattern the rest of the code already uses) in `delete_job_links`, `fetch_urls_for_job`, `update_url_status`, `refresh_job_urls`, `delete_s3_result_file`; removed the dead import-time `job_table` global. Added `TestLazyAwsResourceResolution` regression tests (no import-time AWS globals; helpers resolve their resource at call time). Evidence (local): full backend suite 337 passed (was 334). Decisive verification is PR #7's Backend Tests CI re-run. Merged to claude-main via PR #19. Remaining frontend red signal on PR #7: `E2E Tests` (Playwright, issue #18).
- Frontend CI red-signal fix (claude-main, pending Alex's merge to main). The `claude-main -> main` PR (#7) had the frontend `Unit Tests` and `Lint` checks failing; both were toolchain/config breaks, not product bugs:
  - **Lint:** `pnpm lint` ran `next lint`, which Next.js 16 removed (it parsed `lint` as a project-directory arg and exited 1, so lint had not actually run for some time). Migrated to the ESLint flat config: added `frontend/eslint.config.mjs` (mirrors the prior `next/typescript` ruleset), changed the `lint` script to `eslint .`, and removed `.eslintrc.json`. `no-explicit-any` (75 pre-existing, pervasive in the API/websocket payload layer) is kept as a warning to ratchet down separately; `no-require-imports` is off for config/`.cjs` files where require() is correct; removed one orphaned `react-hooks/exhaustive-deps` disable comment (that rule was never registered under `next/typescript`). Result: `eslint .` exits 0 (0 errors, 106 warnings).
  - **Unit Tests:** CI installs with `--no-frozen-lockfile`, and `@vitejs/plugin-react: latest` resolved to 6.0.1, which imports `vite/internal` (needs Vite 8) and crashed against the Vite 7.3.1 that Vitest 4 bundles (`ERR_PACKAGE_PATH_NOT_EXPORTED`). Pinned `@vitejs/plugin-react` to `^5.1.4` (the proven Vite-7-compatible line already installed locally). Frontend suite stays 51/51 green.
  - Evidence (local): `eslint .` 0 errors / 106 warnings (exit 0); `vitest run` 51 passed; production `next build` succeeded.
- API-key auth wired across the entire /jobs data-plane (claude-main, pending Alex's merge to main). Programmatic API access (the launch "sub-project #2") was blocked because `validate_api_key` existed but was never called: every public endpoint still required a Clerk JWT, so the Settings -> API Keys feature produced keys that did not actually authenticate anything. Added a single auth resolver `resolve_user_id(token)` in `utils.py` that accepts either a SnowScrape API key (`sk_live_...`, checked first by prefix) or a Clerk session JWT, returning the owning user_id (raising on an invalid credential so callers keep their existing 401 path). Wired it into all 13 /jobs data-plane handlers (create, list/status, get, update, delete, pause, cancel, resume, refresh, crawls list+get, download, preview). Control-plane endpoints (api-keys CRUD, billing, integrations/OAuth, templates, webhooks, destinations) intentionally stay Clerk-only. Billing gates are unaffected: they key off user_id, which the resolver supplies for API-key callers too. TDD: 4 resolver unit tests + 2 end-to-end API-key integration tests (valid key authenticates a /jobs read; revoked key -> 401). Evidence: full backend suite 333 passed (308 unit + 25 integration), up from 327.
- Backend red-signal fix (claude-main, pending Alex's merge to main). The backend unit suite was red: 11 failing tests (4 in `test_utils.py`, 7 in `test_ai_extractor.py`). Root causes and fixes:
  - **Real production bug in CSV URL parsing.** `parse_links_from_file`'s pandas path is dead in production (pandas is intentionally not bundled in the Lambda, so it is not in `backend/pyproject.toml` and never imports), meaning the manual `csv.reader` fallback is the ONLY path that runs in prod. That fallback did not skip the header row, did not skip empty cells, and did not support the `'default'` auto-detect column option, so every CSV-sourced job ingested the header text as a bogus URL and could not auto-detect a URL column. Rewrote the fallback to mirror the pandas semantics (row 0 = header, resolve the column against the header, skip the header row and empty cells, support `'default'` via `detect_url_column`). 3 previously-failing `TestParseLinksFromFile` tests now encode the correct behavior and pass.
  - **Stale auth test.** `test_extract_token_case_sensitive` asserted a lowercase `authorization` header yields no token, but `extract_token_from_event` deliberately accepts it (API Gateway V2 lowercases all header names). Corrected the test to match the intended, correct behavior.
  - **AI-extractor test mock drift.** `test_ai_extractor.py` patches `ai_extractor.anthropic`, but the module lazy-imported `anthropic` inside `_get_client`, so the attribute did not exist at patch time (7 failures). Moved `import anthropic` to module scope (it is already a hard dependency); client construction stays lazy. No behavior change.
  - Evidence: backend unit suite 304 passed / 0 failed (was 293 passed, 11 failed); integration suite 23 passed.

### Recent -- 2026-06-05
- Frontend: wired the export-destination selector into the AI-assisted and Visual builder job-creation flows. Previously only the manual form rendered `DestinationSelector`; jobs created via AI/Visual silently dropped any chosen destinations and could never auto-export. Added `export_destination_ids` (plus `source_type`, `url_template`) to `CreateJobDTO`, extracted the `buildAiJobPayload` pure helper with 6 unit tests, and rendered `DestinationSelector` in both flows. Frontend suite 51/51 green. Merged to `claude-main` via PR #6; awaiting Alex's `claude-main -> main` review.

### Recent -- 2026-06-03
- Backend fix: `job_manager.py` now propagates `results_s3_key` into `job_data` before the docs-export fan-out (without it, the export Lambda had no S3 results to read). Committed + pushed to `main`, alongside the Google Docs destination implementation plan and a user-action checklist (`docs/superpowers/plans/2026-06-01-google-docs-destination.md`, `2026-06-02-google-docs-destination-user-checklist.md`).
- Walked Alex through the Google Cloud Console OAuth setup (create project, enable Drive + Docs APIs, configure consent screen, create OAuth client). This is step 1 of the user checklist and the active remaining blocker before the Google Docs destination is live in prod. Context: scoped while evaluating a LinkedIn-post-scraping freelance gig.

---

## What's DONE

### Infrastructure (SST Ion Migration -- Complete)
- Migrated from Serverless Framework to SST Ion v3 (TypeScript IaC, Pulumi engine)
- Merged frontend + backend into unified monorepo with pnpm workspaces
- Migrated API Gateway from V1 (REST) to V2 (HTTP) -- lower latency and cost
- Migrated Python deps from pip/requirements.txt to uv/pyproject.toml
- 29 Lambda functions deployed and operational
- 8 DynamoDB tables with PAY_PER_REQUEST billing, SSE encryption, PITR
- 4 SQS queues (job + webhook, each with DLQ)
- S3 results bucket with versioning and Glacier lifecycle
- Secrets moved from hardcoded to SSM Parameter Store
- CORS restricted to stage-specific origins
- SSRF protection, XPath whitelist, regex timeout validation
- CI/CD via GitHub Actions (frontend + backend workflows)

### 4-Tier Scraping System (Complete)
- Tier 1: Direct HTTP requests (static HTML)
- Tier 2: Residential proxy rotation (IP-blocked sites)
- Tier 3: Firecrawl JS rendering (JavaScript SPAs)
- Tier 4: Firecrawl anti-bot bypass (bot-protected sites)
- Automatic escalation on failure

### AI-Powered Extraction (Complete)
- Claude integration via `ai_extractor.py`
- Natural language queries against scraped content
- Structured data extraction from unstructured HTML

### Real-Time WebSocket (Complete)
- API Gateway V2 WebSocket API
- Live job progress updates
- Connection management with DynamoDB (TTL-enabled)

### Webhook System (Complete)
- Event-driven notifications (job.created, started, completed, failed, cancelled)
- SQS-based async delivery with retry logic (max 3 attempts)
- HMAC SHA256 signatures for security
- Delivery tracking and DLQ for failed deliveries
- Webhook management UI

### Template System (Complete)
- Save and reuse scraping configurations
- Template CRUD with user-scoped access

### Visual Job Builder (Complete)
- No-code job creation UI
- Query builder for XPath, Regex, JSONPath, CSS selectors

### Multi-Format Export (Code-complete; CSV/XLSX/SQL pandas-free on claude-main, awaiting backend deploy)
- JSON (live), CSV, XLSX, SQL export (rewritten pandas-free 2026-06-09, #32; CSV/XLSX formula-injection sanitized 2026-06-10, #34; reach prod on the next backend deploy)
- Parquet: DROPPED as an offered format 2026-06-10 (#33). It needs pyarrow, which is intentionally not bundled in the Lambda (size / cold-start), so it failed 100% of the time. Removed from the UI, client type, backend `valid_formats` (now a clean 400), and all advertising copy. `convert_to_parquet` remains dormant in `format_converter.py`; re-enable later by bundling pyarrow and re-adding the format.
- Server-side conversion with S3 caching

### Frontend (Complete)
- Next.js 16 with App Router
- Tailwind CSS 4.x with semantic color tokens (dark mode)
- Radix UI component library
- Collapsible sidebar layout (reference implementation for SnowForge LLC)
- Marketing landing pages
- Sentry error monitoring
- 42 unit tests (Vitest), Playwright E2E setup

### Google Docs Export Destination (Backend complete; code-ready for deploy)
- OAuth flow for connecting user Google accounts (drive.file + documents scopes; drive.metadata.readonly deferred to v1.1 folder picker)
- KMS-encrypted refresh token storage (per-user)
- Export destinations CRUD (Google Docs as v1 target)
- SQS-triggered docs export Lambda: reads scrape results from S3, formats via three templates (structured_log, compact_list, narrative), writes to user's Drive folder via Google Docs batchUpdate API
- Fan-out from job completion handler: jobs can attach 0-10 destinations; results auto-export after each successful run
- Frontend UI: Integrations page (connect/disconnect Google), Destinations CRUD page, DestinationSelector inside the manual job creation form
- 50+ backend unit + integration tests covering OAuth, destinations, dispatcher, and export Lambda
- Deploy + Doppler secrets + Google Cloud Console OAuth client setup are user-action follow-ups
- Drive folder picker UI deferred to v1.1 (users paste folder ID for now)
- AI/Visual job creation forms now wired with destinations (2026-06-05, PR #6); manual form already had it

### Billing / Stripe Integration (Live in production)

- 14-day Pro trial with card-required checkout (no free starter tier)
- Stripe Customer Portal handles all plan changes, cancellations, payment updates (no in-app plan picker)
- 3 paid tiers: Pro $49/mo, Business $149/mo, Enterprise (sales-led)
- Backend: idempotent Stripe webhook handler with `BillingWebhookDedup` table, race-fixed period-end updates, hard 402 gate at job-create when subscription inactive, fail-open usage counters
- Frontend: subscription-status proxy gate (60s cookie cache, only caches `trialing`/`active`), `/onboarding/checkout` and `/billing/locked` screens, Settings → Billing tab live data, one-time-secret API-key modal
- Pricing page: dropped Starter card, 14-day-trial hero, `<PricingCTA>` routes signed-out → /sign-up, signed-in active → portal, signed-in no-sub → /onboarding/checkout
- Tests: 11 backend webhook + integration tests, 3 Vitest unit tests, 1 Playwright E2E (gated on Clerk test user)
- **Deployed to dev** (test mode) on 2026-05-07: smoke test passed end-to-end (signup → checkout → trial → cancel → past-due lockout → webhook idempotency replay)
- **Deployed to prd** (live mode) on 2026-05-08: backend + frontend live; awaiting first real $0 trial signup as final acceptance
- Live Stripe identifiers (test mode): Pro `price_1TUYHnAnsCk0eFqBMfkFoAaj`, Business `price_1TUYHzAnsCk0eFqBcXokmvKv`, Portal config `bpc_1TUYIIAnsCk0eFqBGb41J2Zv`, Webhook `we_1TUat5AnsCk0eFqBGBqPX87U`
- Live Stripe identifiers (live mode): Pro `price_1TUf3bAhxqX4McFQyyCQu6Tq`, Business `price_1TUf3mAhxqX4McFQlhAp2mCF`, Portal config `bpc_1TUf3vAhxqX4McFQ2R2Tb72j`, Webhook `we_1TUfJPAhxqX4McFQM0W5R5M7`
- Production frontend: `https://scrape.snowforge.dev` (Vercel)
- Production API: `https://2pg2gj4048.execute-api.us-east-2.amazonaws.com`

---

## What's NOT DONE

### Analytics Dashboard (UI only, no data)
- Dashboard pages exist but display mock/placeholder data
- No real analytics pipeline connected

### API Key Authentication (jobs data-plane wired on claude-main; control-plane still Clerk-only)
- Backend `api_key_handler.py` and Settings → API Keys tab fully implemented (one-time-secret modal, list/create/revoke)
- API keys can be created and managed
- DONE (claude-main, 2026-06-06): `Authorization: Bearer sk_live_...` now authenticates the entire `/jobs` data-plane via `resolve_user_id` (create, list, get, update, delete, pause, cancel, resume, refresh, crawls, download, preview)
- DONE (claude-main, 2026-06-07): public API docs + programmatic quickstart at `docs/API.md`, and `backend/openapi.yml` now documents the dual auth model (`ApiKeyAuth` scheme + `security` on the 13 data-plane ops), guarded by `test_openapi_spec.py`
- Remaining: decide whether to extend API-key auth to the other data endpoints (templates, webhooks, export destinations); the control-plane (api-keys CRUD, billing, integrations/OAuth) stays Clerk-only by design.
- Sub-project #2 of launch sequence

### Notification System (Partial)
- Webhook notifications work
- Email notifications not implemented
- In-app notification center not built

### Known Technical Limitations
- JavaScript rendering: GLIBC incompatibility blocks Playwright on Lambda (Tiers 3/4 use Firecrawl instead)
- No Redis cache (planned but not implemented)
- Single region (us-east-2, no multi-region failover)
- Lambda runs in default VPC

---

## Estimates to Revenue

| Work Item | Estimate | Priority |
|-----------|----------|----------|
| First real $0 trial signup as final live smoke | hours | CRITICAL -- final acceptance |
| API key auth on public endpoints | jobs data-plane DONE (2026-06-06); API docs + openapi spec DONE (2026-06-07); optional: extend to templates/webhooks/destinations | MEDIUM |
| Real analytics data pipeline | 2-3 weeks | HIGH |
| Email notifications | 1 week | MEDIUM |
| In-app notification center | 1 week | LOW |
| `@snowforge/ui` v3→v4 migration + revert `typescript.ignoreBuildErrors` | 1-2 hours | LOW (debt) |

---

## Architecture Reference

See [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md) for full details on:
- 29 Lambda functions with memory/timeout configs
- 8 DynamoDB tables with GSIs and encryption
- 4 SQS queues with retry and DLQ configuration
- S3 lifecycle policies
- Environment variables
- Cost estimates
- Security policies
