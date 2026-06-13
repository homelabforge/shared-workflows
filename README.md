# homelabforge/shared-workflows

Reusable GitHub Actions workflows for HomeLabForge Python+React repos.

Pinned via versioned tags (`v1.0.0`, `v1.1.0`, …). Consumers MUST pin to a
released tag — never `@main`, never a branch.

## Workflows

| File | Purpose | Used by |
|---|---|---|
| `python-react-ci.yml` | CI: shared test suite + pg-migrations + docker-build-test | familycircle, mygarage, tidewatch, vulnforge |
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
    uses: homelabforge/shared-workflows/.github/workflows/python-react-ci.yml@v1.4.2
    with:
      enable-translations: true            # mygarage
      enable-bootstrap-token: true         # vulnforge
      enable-e2e: false                    # familycircle
      enable-pg-migrations: true           # mygarage (>=v1.2.0)
      security-tripwire-script: .github/scripts/security-tripwire.sh
```

Per-repo flags (actual values in production):

| Repo | enable-e2e | enable-translations | enable-bootstrap-token | enable-pg-migrations | enable-api-freshness-check | tripwire-script |
|---|---|---|---|---|---|---|
| familycircle | false | (default) | (default) | (default) | (default) | `.github/scripts/security-tripwire.sh` |
| mygarage | (default) | true | (default) | true | (default) | `.github/scripts/security-tripwire.sh` |
| tidewatch | (default) | (default) | (default) | (default) | (default) | `.github/scripts/security-tripwire.sh` |
| vulnforge | (default) | (default) | true | (default) | (default) | `.github/scripts/security-tripwire.sh` |

### `enable-pg-migrations` (v1.2.0+)

When `true`, runs the consumer's `docker-compose.test.yml` stack and
exercises `pytest tests/migrations/` against a real PostgreSQL sidecar
(in addition to the SQLite path the standard `test-backend` job uses).

This is the path that catches PG dialect bugs in migrations — `DATETIME`
vs `TIMESTAMP`, `ADD CONSTRAINT IF NOT EXISTS`, etc. — that the SQLite
test path silently passes. mygarage adopted this in v2.27.0-rc2 after
a real rc1 incident; other consumers can opt in once they ship a
`docker-compose.test.yml` and a `backend/Dockerfile.test`.

Customization (rare — defaults match the mygarage pattern):

| Input | Default | Purpose |
|---|---|---|
| `pg-migrations-compose-file` | `docker-compose.test.yml` | Compose file path |
| `pg-migrations-service` | `mygarage-test` | Compose service that runs pytest |
| `pg-migrations-pytest-path` | `tests/migrations/` | What pytest invokes (mygarage overrides to also include `tests/integration/`) |

### Publish (consumer `.github/workflows/publish.yml`)

```yaml
name: Publish

on:
  push:
    tags: ['v*.*.*']

jobs:
  publish:
    uses: homelabforge/shared-workflows/.github/workflows/python-react-publish.yml@v1.4.2
    with:
      enable-translations: true            # mygarage
      enable-bootstrap-token: true         # vulnforge
      enable-e2e: false                    # familycircle
      security-tripwire-script: .github/scripts/security-tripwire.sh
      image-name: homelabforge/<repo>      # e.g. homelabforge/tidewatch
      release-name-prefix: '<Repo> v'      # e.g. 'TideWatch v'
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
    uses: homelabforge/shared-workflows/.github/workflows/codeql.yml@v1.4.2
    with:
      python-extension-pack: homelabforge/tidewatch-models  # tidewatch only
```

### Dependabot Auto-Merge (consumer `.github/workflows/dependabot-auto-merge.yml`)

```yaml
name: Dependabot Auto-Merge

on:
  pull_request:

jobs:
  auto-merge:
    uses: homelabforge/shared-workflows/.github/workflows/dependabot-auto-merge.yml@v1.4.2
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Bun version pinning

Every workflow reads bun version from the consumer repo's `.bun-version`
file (single source of truth). The `bun-version` input is an escape hatch
for emergency overrides — leave empty to use the file.

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
