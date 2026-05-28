# Changelog

All notable changes to homelabforge/shared-workflows will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.1] - 2026-05-28

### Fixed
- `python-react-ci.yml` and `python-react-publish.yml` called the internal
  `_python-react-tests.yml` building block via a `./` local path. A `./` reference
  inside a reusable workflow that is invoked cross-repo resolves against the
  **consumer's** repository (which has no such file), not shared-workflows, so every
  consumer pinned at `v1.4.0` hit an instant 0-second `startup_failure`
  (`workflow was not found`). actionlint does not catch this. Both call sites now use
  the full `homelabforge/shared-workflows/.github/workflows/_python-react-tests.yml@v1.4.1`
  path. The `@ref` is self-referential and must be bumped on every future release.

## [1.4.0] - 2026-05-28

### Changed
- Extracted the shared backend/frontend/e2e/api-freshness matrix into an internal
  `_python-react-tests.yml` building block that both `python-react-ci.yml` and
  `python-react-publish.yml` call — eliminates ~150 lines of duplicated job YAML and
  a real drift it had already caused (the frontend-install `dependabot[bot]`
  conditional existed in CI but not in publish).
- Publish workflow's `docker`/`release` gates simplified to plain `needs:` — a
  skipped optional job no longer fails the shared `tests` job, so the previous
  `always() && needs.*.result == 'success'` guards are no longer required.
- Publish `docker` now gates on the full shared `tests` job, which **includes E2E**.
  Previously `docker` listed only `test-backend`/`test-frontend`/`api-types-freshness`
  in `needs:`, so a red E2E did not block the image push; it now does.
- `pg-migrations` now `needs: [tests]` (was `needs: [test-backend]`, no longer
  addressable now that the test jobs live inside the reusable suite). Without this it
  ran even when backend lint/type/unit tests had already failed.
- CodeQL: dropped the per-language toolchain setup and dependency-install steps.
  `build-mode: none` scans source directly and Python dependency installation has
  had no effect on results since CodeQL 2.16 (Jan 2024); `build-mode` is now wired
  through to the `init` action. Analysis `timeout-minutes` lowered from 360 to 45.
- Added explicit `timeout-minutes` to the frontend, api-freshness, docker-build-test,
  and publish `docker`/`release` jobs (previously defaulted to the 6-hour ceiling).
  Backend pytest's inner `timeout` lowered 25m → 20m so it reports before the job cap.

### Migration (required when bumping consumers)
- **Status-check context names change.** Nesting the test jobs inside the reusable
  `tests` job renames the four test checks: `ci / Backend Tests` →
  `ci / tests / Backend Tests` (likewise Frontend Tests, E2E Tests, API Types
  Freshness). `ci / Docker Build Test`, `ci / PostgreSQL Migration Tests`, and the
  `codeql / *` checks are unchanged.
- Any consumer with branch protection requiring the old names will have PRs stuck on
  "Expected — waiting for status" until the required-status-check contexts are
  updated. Affects the public repos (mygarage, tidewatch, vulnforge, familycircle);
  private free-tier repos have no branch protection and are unaffected.
- Recommended rollout: tag a `-rc1`, run it on one consumer PR to capture the exact
  new context strings, update branch protection, then bump the rest.

## [1.3.1] - 2026-05-27

### Changed
- Roll forward action SHAs merged in PR #2 (`codeql-action` 4.35.1 → 4.35.4, `upload-artifact` 7.0.0 → 7.0.1, `setup-uv` 8.0.0 → 8.1.0) so consumers pinned at `v1.3.x` pick them up

### Added
- `.github/workflows/dependabot-auto-merge.yml` self-hosted on `@main` — repo now consumes its own auto-merge workflow so future dependabot PRs merge without manual review
- `CHANGELOG.md` (this file), backfilled from tag history
- README: consumer list and Per-repo flags table updated to match production; pre-release tag semantics documented in the Publish recipe

## [1.3.0] - 2026-05-09

### Changed
- Bump 5 GitHub Actions to node24 runners (PR #1) and add `.github/dependabot.yml` to keep action SHAs current

## [1.2.0] - 2026-05-05

### Added
- `pg-migrations` job opt-in via `enable-pg-migrations: true` — runs the consumer's `docker-compose.test.yml` stack against a real PostgreSQL sidecar so migrations with PG-only dialect bugs (`DATETIME` vs `TIMESTAMP`, `ADD CONSTRAINT IF NOT EXISTS`) fail in CI instead of slipping through SQLite tests
- `pg-migrations-compose-file`, `pg-migrations-service`, `pg-migrations-pytest-path` inputs for consumers whose layout differs from mygarage's

## [1.1.3] - 2026-05-04

### Fixed
- Publish workflow's `release` job needs an explicit `always()` guard for its `if:` expression to evaluate at all

## [1.1.2] - 2026-05-04

### Fixed
- Publish workflow gates the release job explicitly on `docker.result == 'success'`

## [1.1.1] - 2026-05-03

### Fixed
- Publish workflow allows the `docker` job to proceed when `api-types-freshness` is skipped (was previously blocked by the conditional-need evaluation)

## [1.1.0] - 2026-05-01

### Added
- Pre-release tag detection (`vX.Y.Z-rcN`, `vX.Y.Z-betaN`, `vX.Y.Z-alphaN`) — publishes only the exact `:VERSION` image, leaving `:latest`, `:MAJOR`, `:MINOR` pinned to the last stable

## [1.0.0] - 2026-04-27

### Added
- Initial reusable workflows for Python+React homelab repos: `python-react-ci.yml`, `python-react-publish.yml`, `codeql.yml`, `dependabot-auto-merge.yml`
- `templates/bin/ci-check` copy-and-customize script for local-dev CI parity
- `lint.yml` self-check (actionlint over every reusable workflow)
