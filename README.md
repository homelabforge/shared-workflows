# homelabforge/shared-workflows

Reusable GitHub Actions workflows for HomeLabForge Python+React repos.

Pinned via versioned tags (`v1.0.0`, `v1.1.0`, …). Consumers MUST pin to a
released tag — never `@main`, never a branch.

## Workflows

| File | Purpose | Used by |
|---|---|---|
| `python-react-ci.yml` | CI: ruff + pyright + pytest + frontend gates + E2E + api-freshness + docker-build-test | familycircle, mygarage, tidewatch, vulnforge |
| `python-react-publish.yml` | Tag publish: test → docker push → release | same |
| `codeql.yml` | CodeQL python + javascript matrix | same |
| `dependabot-auto-merge.yml` | Dependabot PR auto-merge (patch + minor) | same |

CollectionSync is intentionally not standardized on these (private repo,
different release/codeql stack). MyGarage's `translations.yml` stays
repo-local — single consumer, doesn't justify extraction.

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
    uses: homelabforge/shared-workflows/.github/workflows/python-react-ci.yml@v1.0.0
    with:
      enable-translations: true            # mygarage
      enable-bootstrap-token: true         # vulnforge
      enable-e2e: false                    # familycircle
      security-tripwire-script: .github/scripts/security-tripwire.sh
```

Per-repo flags:

| Repo | enable-e2e | enable-translations | enable-bootstrap-token | tripwire-script |
|---|---|---|---|---|
| familycircle | false | (default) | (default) | `.github/scripts/security-tripwire.sh` |
| mygarage | (default) | true | (default) | `.github/scripts/security-tripwire.sh` |
| tidewatch | (default) | (default) | (default) | `.github/scripts/security-tripwire.sh` |
| vulnforge | (default) | (default) | true | `.github/scripts/security-tripwire.sh` |

### Publish (consumer `.github/workflows/publish.yml`)

```yaml
name: Publish

on:
  push:
    tags: ['v*.*.*']

jobs:
  publish:
    uses: homelabforge/shared-workflows/.github/workflows/python-react-publish.yml@v1.0.0
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
    uses: homelabforge/shared-workflows/.github/workflows/codeql.yml@v1.0.0
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
    uses: homelabforge/shared-workflows/.github/workflows/dependabot-auto-merge.yml@v1.0.0
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
block at the top of the script.

## Versioning

Tag via semver: `v1.0.0`, `v1.0.1`, …
- Patch: bug fixes, no behavior change
- Minor: new optional inputs, new optional jobs, default-preserving
- Major: breaking input/job changes

Cut RC tags first (`v1.x.0-rc.1`) and canary on MyGarage before promoting.

## Linting

`actionlint` runs on every push via `.github/workflows/lint.yml`.
