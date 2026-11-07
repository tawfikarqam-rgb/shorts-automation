# YouTube Automation Agent — GitHub Actions Adaptation

## Decision

Adapt `darkzOGx/youtube-automation-agent` for scheduled, ephemeral GitHub Actions runs. Do not run its built-in always-on dashboard server or `node-cron` scheduler in Actions. Reuse its production/research/publishing capabilities through a bounded headless runner.

## Existing production contract (preserve)

- Channels: `business` and `history`, isolated per-channel configuration and YouTube OAuth credentials.
- Existing scheduled workflow remains enabled and unchanged during migration: `.github/workflows/moneyprinter-turbo-daily.yml`.
- Existing schedule: `15 19 * * *`, timezone `Africa/Cairo`.
- Existing duplicate ledger and fail-closed publication guard: `scripts/publish_guard.py`, `state/published/{business,history}.json`.
- Preserve per-channel publication behavior and existing GitHub secrets/vars until the replacement passes end-to-end validation.
- No generated video may upload unless media, narration, metadata, provenance/evidence, and duplicate checks pass.
- Upload outcome ambiguity must stop retries and require reconciliation; never blindly upload again.

## Upstream project assessment

Upstream: `darkzOGx/youtube-automation-agent` (MIT; Node.js >=18.17; package version 2.11.0).

The upstream application is designed as a persistent self-hosted Node.js dashboard with an internal `node-cron` scheduler and local SQLite database. Its documented quick start is interactive (`npm run walkthrough`, then `npm start`). It does not document a non-interactive, one-shot GitHub Actions command that generates one channel's video and exits. Therefore, invoking its normal scheduler/server from Actions is not a valid integration.

Relevant upstream capabilities include staged production, resumable checkpoints, evidence/provenance checks, narration validation, real-MP4 validation, and fail-closed publishing. The publishing agent also blocks simulated assets, missing narration, failed readiness, and unresolved upload outcomes.

## Target architecture

1. GitHub Actions remains the only scheduler and launches one isolated job per channel.
2. A new headless adapter invokes selected upstream agent services for exactly one channel/run and exits with a machine-readable result.
3. GitHub Actions supplies provider credentials and per-channel configuration via secrets; never commit credentials or OAuth tokens.
4. Persist resumable production state and durable ledgers outside the ephemeral runner. Do not rely on SQLite files surviving between GitHub-hosted jobs.
5. Keep the current duplicate ledger as the authoritative cross-run publication guard until an equivalent tested implementation is proven.
6. Keep research, generation, media validation, metadata validation, evidence/provenance, duplicate reservation, YouTube upload, and publication confirmation as explicit gates.
7. Automatic publishing is permitted only after every gate passes. Any missing provider, malformed output, insufficient evidence, simulated media, narration failure, duplicate, or ambiguous upload outcome must fail closed.

## Migration phases

### Phase 0 — Baseline and safety (this branch)
- Record the current workflow contract and upstream compatibility constraints.
- Keep `main` and the active production workflow untouched.

### Phase 1 — Headless compatibility spike
- Inspect upstream app initialization, database schema, credential manager, generation orchestration, and publishing agent.
- Identify a supported service-level invocation path that does not start Express or node-cron.
- Build a one-channel dry-run adapter with no YouTube upload permission.
- Pin the upstream source to a reviewed tag/commit; do not track a moving branch.

### Phase 2 — Persistence and safety adapter
- Define durable state/checkpoint storage suitable for ephemeral runners.
- Integrate the existing per-channel duplicate ledger and reserve/confirm/reconcile lifecycle.
- Add tests for duplicate topic/script/video, missing narration, simulated media, evidence failures, and uncertain upload outcomes.

### Phase 3 — Workflow integration
- Add a separate candidate workflow on this branch, retaining the current production workflow unchanged.
- Preserve the current schedule and timezone unless explicitly approved otherwise.
- Initially run in dry-run mode; upload must be disabled by default.

### Phase 4 — End-to-end validation and cutover
- Validate both channels independently, including generated MP4 decoding and metadata/evidence checks.
- Enable automatic publishing only after successful non-publishing validation and explicit confirmation of the cutover.
- Do not disable the old workflow until the replacement has passed validation and the user approves cutover.

## Known blockers / decisions to resolve during the spike

- Upstream's documented OAuth setup uses a Desktop OAuth client and interactive walkthrough. Actions requires a secure non-interactive refresh-token path; this must be verified before implementation.
- Upstream's local SQLite database and media/checkpoint files are ephemeral on GitHub-hosted runners. A deliberate persistence strategy is required.
- Upstream currently documents manual review as its default publishing gate. The requested automatic mode must be implemented as a narrowly scoped policy that still requires all factual, rights, media, narration, metadata, and duplicate checks; it must not bypass readiness/provenance checks.
- The upstream repository's `master` branch is not a safe dependency pin. Select a reviewed release commit before vendoring or cloning it in CI.

## Acceptance criteria

- No changes to the active production workflow during the spike.
- No credentials in repository files, logs, artifacts, or generated diagnostics.
- One bounded job per channel, no long-running server or cron process.
- State survives separate workflow runs.
- All safety gates are covered by automated tests.
- Upload happens only after durable reservation; successful upload is confirmed in the ledger; uncertain outcomes block retries.


## Phase 1 spike findings

- `index.js` constructs the Express app, credential manager, database, agents, and `DailyAutomation`; its normal initialization starts the scheduler. It is not suitable as the Actions entrypoint.
- `CredentialManager` reads `config/credentials.json`; its setup path uses Inquirer and a localhost OAuth callback. Actions cannot run that interactive setup. A dedicated non-interactive credential loader is required, with the refresh token supplied through GitHub Secrets and no credential file committed.
- `Database` uses local SQLite. GitHub-hosted runners are ephemeral, so upstream SQLite checkpoints, queue rows, and media files disappear after a job unless explicitly persisted.
- `ProductionManagementAgent.processContent(contentData)` is a potentially reusable service-level production entrypoint, but its complete initialization dependencies and output contract must be mapped before calling it directly.
- `PublishingSchedulingAgent.publishContent(contentId)` contains useful fail-closed checks for readiness, provenance, narration, and uncertain upload outcomes. Its database schedule entry model and OAuth integration must be adapted to the existing durable GitHub ledger before it can be used safely.
- The upstream README's documented setup is interactive; no documented one-shot command exists for a single-channel generate-and-exit run.

### Phase 1 implementation boundary

Do not call `YouTubeAutomationAgent.initialize()` in a GitHub Actions job: it starts the Express/dashboard and daily scheduler. Build a separate CLI entrypoint that initializes only the required services, accepts an explicit channel, executes one bounded generation, emits structured status, and exits. Publishing stays disabled in the first spike.
