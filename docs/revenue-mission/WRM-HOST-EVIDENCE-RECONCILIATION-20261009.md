# WRM host evidence reconciliation — 2026-10-09
Status: OBSERVATION_ONLY / WRM_LIVE_CYCLE_NOT_PROVEN.

## Direct read-only provider receipts
- runtime branch: `runtime/durable-asp-control`.
- `runtime/manifest.json`: last_operation=`bootstrap`, last_event_id=`execution-protocol-001-bootstrap-001`, runtime_source_revision=`f60c90cd349a2a190e00daed671d4602c1a1e73c`, persistent_provider_trigger_enabled=true, authority_created=false.
- Database SHA-256: `sha256:2f73e525937be87195fa4005e6842755bcc8553d3529346ff89dddbe7433c3ca`. Manifest presence proves a persisted receipt, not currently running scheduler or WRM execution.
- Native host candidate remains at `runtime-candidates/durable-runtime-burst-host.yml`, not active `.github/workflows/`. Candidate pins `590ef646883e408b4632ea4177f7229d9fe0ac5b`, distinct from manifest runtime source `f60c90cd...`; do not assume equivalence without verification.
- AB-NRA-001 verification for `112d6c65423112fe65da3181c29fcfb9f8fb1762`: GitHub Actions run `37581315184` completed SUCCESS. This is a test/rehearsal, not live WRM.
- PR #44 head `489205e00e2a04bf2ebd677f20db777ceb612ebb`: main integration gate run `37984934500`, Constitution Gate `37984934360`, terminal verification `37984934352`, all SUCCESS. Terminal verification included live runtime evidence fetching, but its success alone does not demonstrate a WRM burst or activation.

## Controlled rehearsal evidence already present
`tests/test_persistent_burst_host.py` includes a deterministic 3-event scenario, successive committed generations 1/2/3 and HUMAN_GATE terminal with authority_created=false; negative tests include start-state and content digest mismatch. These are synthetic test fixtures. No fresh WRM-specific live host rehearsal was executed by this reconciliation.

## Decision
Candidate host VERIFIED_BY_EXISTING_CI; persisted base runtime OBSERVED; WRM-native live activation NOT_PROVEN. HOLD activation and repin. Next admissible work: inspect exact active workflow and runtime lease, then execute isolated read-only/dry-run WRM-specific replay with immutable receipts, verifying recovery and human stop before seeking explicit bounded activation authority. No additional spending or credentials.
