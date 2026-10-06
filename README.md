# homelabforge/shared-workflows

Reusable GitHub Actions workflows for HomeLabForge Python+React repos.
MyGarage is the only active consumer: every other app was archived on
2026-09-16, and their pins are frozen at whatever tag they last used.

Pinned via versioned tags (`v1.0.0`, `v1.1.0`, …). Consumers MUST pin to a
released tag — never `@main`, never a branch.

## Workflows

| File | Purpose | Used by |
|---|---|---|
| `python-react-ci.yml` | CI: shared test suite + pg-migrations + docker-build-test | mygarage |
| `python-react-publish.yml` | Tag publish: shared test suite → docker push → release | same |
| `_python-react-tests.yml` | Internal building block: ruff + pyright + pytest + frontend gates + E2E + api-freshness. Called by CI and publish — not for direct consumer use | (internal) |
| `codeql.yml` | CodeQL python + javascript matrix | same |
| `dependabot-auto-merge.yml` | Dependabot PR auto-merge (patch + minor) | same |

MyGarage's `translations.yml` stays repo-local — single consumer,
doesn't justify extraction.

## Required status checks

Consumers wrap these with a job named `ci` (and `codeql`), so check contexts are
named `<job> / <name>`. The test-suite jobs run inside the nested
`_python-react-tests.yml`, so they report one level deeper:

- `ci / tests / Backend Tests`
- `ci / tests / Frontend Tests`
- `ci / tests / E2E Tests`
- `ci / tests / API Types Freshness`

The CI-local jobs keep the flat form: `ci / Docker Build Test`,
`ci / PostgreSQL Migration Tests`. CodeQL reports `codeql / Analyze (python)` and
`codeql / Analyze (javascript)`. When adopting or upgrading, update each repo's
branch-protection required-check contexts to match — a renamed-but-still-required
check blocks PRs indefinitely.

Since v1.7.0, `Backend Tests`, `Frontend Tests`, `E2E Tests` and
`ci / PostgreSQL Migration Tests` are held by small keeper jobs that wait on
every part of their suite (the checks job and every shard) and fail unless all
of them passed. They run `if: always()`, so a skipped or cancelled shard can't
read as green. `API Types Freshness` is unchanged: still its own conditional
job, waiting on `Backend Tests`. A suite turned off on purpose
(`enable-e2e: false`, `enable-pg-migrations: false`) still skips its keeper,
same as before.

The shard jobs (`... (1/3)`) and `Backend Checks` / `Frontend Checks` are not
meant to be required; the keepers already wait on them. Requiring a shard job
wedges every PR the day its shard count changes.

## Wrapper recipes

### CI (consumer `.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  ci:
    uses: homelabforge/shared-workflows/.github/workflows/python-react-ci.yml@v1.7.0
    with:
      enable-translations: true
      enable-pg-migrations: true           # >=v1.2.0
      security-tripwire-script: .github/scripts/security-tripwire.sh
      backend-test-shards: 2               # >=v1.7.0, see "Test shards"
      frontend-test-shards: 3
      e2e-test-shards: 2
      pg-migrations-shards: 3
```

Production flags (mygarage):

| Repo | enable-e2e | enable-translations | enable-bootstrap-token | enable-pg-migrations | enable-api-freshness-check | tripwire-script |
|---|---|---|---|---|---|---|
| mygarage | (default) | true | (default) | true | (default) | `.github/scripts/security-tripwire.sh` |

### `enable-pg-migrations` (v1.2.0+)

When `true`, runs the consumer's `docker-compose.test.yml` stack and
exercises `pytest tests/migrations/` against a real PostgreSQL sidecar
(in addition to the SQLite path the standard backend test jobs use).

This is the path that catches PG dialect bugs in migrations — `DATETIME`
vs `TIMESTAMP`, `ADD CONSTRAINT IF NOT EXISTS`, etc. — that the SQLite
test path silently passes. mygarage adopted this in v2.27.0-rc2 after
a real rc1 incident.

Customization (rare — defaults match the mygarage pattern):

| Input | Default | Purpose |
|---|---|---|
| `pg-migrations-compose-file` | `docker-compose.test.yml` | Compose file path |
| `pg-migrations-service` | `mygarage-test` | Compose service that runs pytest |
| `pg-migrations-pytest-path` | `tests/migrations/` | What pytest invokes (mygarage overrides to also include `tests/integration/`) |
| `pg-migrations-shards` | `1` | v1.7.0+: runners the PG run is split across, each with its own sidecar (see "Test shards") |

### Test shards (v1.7.0+)

Four inputs split the long suites across parallel runners: `backend-test-shards`,
`frontend-test-shards`, `e2e-test-shards` (CI and publish) and
`pg-migrations-shards` (CI only). Each takes 1 to 6 and defaults to 1, which is
the old behaviour apart from the job names. Retuning one is a one-line change in
the consumer's `ci.yml`.

- **Vitest and Playwright** use their own `--shard=k/N`. The workflow runs
  `bun run test:run --shard=k/N` and `bun run e2e --shard=k/N`, so both scripts
  have to pass extra args through to the tool.
- **Pytest** has no `--shard`, so the consumer's `conftest.py` needs a hook that
  reads the env below, keeps its share of whole test modules and writes a report.
  The keeper then fails the run unless the reports cover every collected module
  exactly once (`.github/actions/verify-pytest-shards`). A consumer without the
  hook works at 1 shard; above 1 every shard runs the whole suite, then fails
  its "Upload shard report" step (no `pytest-shard-report.json`), so the keeper
  goes red. mygarage's `backend/tests/_shard.py` is the reference hook.

The pytest contract, set on every pytest run in a sharded job (backend and PG):

| Variable | Value |
|---|---|
| `PYTEST_SHARD_INDEX` | this runner's shard, 1-based (`matrix.shard`) |
| `PYTEST_SHARD_COUNT` | number of shards (`strategy.job-total`) |
| `PYTEST_SHARD_REPORT` | `pytest-shard-report.json`, relative to pytest's rootdir |

The rootdir is `backend/` in both jobs. In the PG job pytest runs in the compose
service, so the service has to bind-mount `./backend` at its rootdir (mygarage's
`./backend:/app`); that puts the report at `backend/pytest-shard-report.json`
on the runner, where the upload step looks for it.

Report, schema 1:

```json
{
  "schema": 1,
  "index": 2,
  "count": 3,
  "modules": ["tests/migrations/test_a.py", "..."],
  "selected": ["tests/migrations/test_b.py", "..."]
}
```

`modules` is every collected module in collection order, after `-k`/`-m`
deselection. `selected` is this shard's share, in the same order. Don't name
the report as a dotfile: `upload-artifact` skips hidden files.

### Publish (consumer `.github/workflows/publish.yml`)

```yaml
name: Publish

on:
  push:
    tags: ['v*.*.*']

jobs:
  publish:
    uses: homelabforge/shared-workflows/.github/workflows/python-react-publish.yml@v1.7.0
    with:
      enable-translations: true
      security-tripwire-script: .github/scripts/security-tripwire.sh
      image-name: homelabforge/mygarage
      release-name-prefix: 'MyGarage v'
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

Pre-release tags (`vX.Y.Z-rcN`, `vX.Y.Z-betaN`, `vX.Y.Z-alphaN`) publish
only the exact `:VERSION` image — `:latest`, `:MAJOR`, `:MINOR` stay
pinned to the last stable. Use plain `vX.Y.Z` for stable releases.

### CodeQL (consumer `.github/workflows/codeql.yml`)

```yaml
name: CodeQL

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 6 * * 1'

jobs:
  codeql:
    uses: homelabforge/shared-workflows/.github/workflows/codeql.yml@v1.7.0
```

### Dependabot Auto-Merge (consumer `.github/workflows/dependabot-auto-merge.yml`)

```yaml
name: Dependabot Auto-Merge

on:
  pull_request:

jobs:
  auto-merge:
    uses: homelabforge/shared-workflows/.github/workflows/dependabot-auto-merge.yml@v1.7.0
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Bun version pinning

Every workflow reads bun version from the consumer repo's `.bun-version`
file (single source of truth). The `bun-version` input is an escape hatch
for emergency overrides — leave empty to use the file.

## Node version pinning

The frontend, E2E and API-freshness jobs also set up Node from the consumer
repo's `.nvmrc` (`node-version-file` input). vitest, eslint, tsc and Playwright
run on Node even under `bun run`, because their bins are
`#!/usr/bin/env node`; before this they got the runner image's default Node.
The file is required: a missing `.nvmrc` fails the job instead of falling back
silently. `node-version` is the escape hatch. `templates/bin/ci-check` checks
the host's Node major against the same file.

## bin/ci-check template

`templates/bin/ci-check` is a copy-into-your-repo template that gives
local-dev parity with these workflows. Per-repo deltas live in a config
block at the top of the script. Consumer copies drift intentionally as
each repo customizes its own block — re-syncing wholesale would clobber
those edits.

## Versioning

Tag via semver: `v1.0.0`, `v1.0.1`, …
- Patch: bug fixes, action SHA bumps, no behavior change
- Minor: new optional inputs, new optional jobs, default-preserving
- Major: breaking input/job changes

For risky changes, cut RC tags first (`v1.x.0-rc1`) and canary on MyGarage
before promoting.

See `CHANGELOG.md` for the per-release history.

## Self-hosted dogfooding

This repo consumes its own reusable workflows:
- `.github/workflows/dependabot-auto-merge.yml` calls the reusable auto-merge
  at `@main` (the only repo where `@main` is acceptable — it can't lag itself).
- `.github/workflows/lint.yml` runs `actionlint` on every push as a self-check
  against malformed reusable workflow syntax.
