# Changelog

All notable changes to homelabforge/shared-workflows will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.1] - 2026-05-27

### Changed
- Roll forward action SHAs merged in PR #2 (`codeql-action` 4.35.1 → 4.35.4, `upload-artifact` 7.0.0 → 7.0.1, `setup-uv` 8.0.0 → 8.1.0) so consumers pinned at `v1.3.x` pick them up

### Added
- `.github/workflows/dependabot-auto-merge.yml` self-hosted on `@main` — repo now consumes its own auto-merge workflow so future dependabot PRs merge without manual review
- `CHANGELOG.md` (this file), backfilled from tag history
- README: collectionsync and myhealth listed as consumers; Per-repo flags table updated to match production; pre-release tag semantics documented in the Publish recipe

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
