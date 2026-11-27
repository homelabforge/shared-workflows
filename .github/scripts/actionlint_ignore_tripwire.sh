#!/usr/bin/env bash
# Tripwire for the `$/` ignore in .github/actionlint.yaml. Runs actionlint with
# no config, so the ignore is off, and fails once it stops flagging our `$/` refs.
# The image comes from lint.yml and the pattern from actionlint.yaml, so a bump
# there is what this tests.
# Usage: actionlint_ignore_tripwire.sh [repo-root]
set -uo pipefail
export LC_ALL=C

root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
lint_yml="$root/.github/workflows/lint.yml"
config="$root/.github/actionlint.yaml"

broken() {
  echo "tripwire: $*" >&2
  exit 2
}

# The one actionlint image lint.yml runs, and it has to be digest-pinned.
[[ -f "$lint_yml" ]] || broken "$lint_yml not found"
mapfile -t images < <(grep -oE 'docker://rhysd/actionlint[^[:space:]]*' "$lint_yml")
[[ ${#images[@]} -eq 1 ]] || broken "want exactly one actionlint image in lint.yml, found ${#images[@]}"
[[ "${images[0]}" =~ ^docker://(rhysd/actionlint@sha256:[0-9a-f]{64})$ ]] ||
  broken "lint.yml's actionlint image isn't digest-pinned: ${images[0]}"
image="${BASH_REMATCH[1]}"

# The ignore entry for `$/`, unquoted from its single-quoted YAML string.
[[ -f "$config" ]] || broken "$config not found"
mapfile -t ignores < <(grep -F '\$/' "$config" |
  sed -nE "s/^[[:space:]]*-[[:space:]]*'(.+)'[[:space:]]*\$/\1/p")
[[ ${#ignores[@]} -eq 1 ]] || broken "want exactly one \$/ ignore in actionlint.yaml, found ${#ignores[@]}"
diagnostic="${ignores[0]//\'\'/\'}"

# Probe the first workflow that still has a `$/` ref.
shopt -s nullglob
workflows=("$root"/.github/workflows/*.yml "$root"/.github/workflows/*.yaml)
[[ ${#workflows[@]} -gt 0 ]] || broken "no workflows under $root/.github/workflows"
target=""
for f in "${workflows[@]}"; do
  if grep -qE "^[[:space:]]*(-[[:space:]]+)?uses:[[:space:]]*[\"']?\\\$/" "$f"; then
    target="$f"
    break
  fi
done
if [[ -z "$target" ]]; then
  echo "tripwire: no \`\$/\` refs left in .github/workflows, so the ignore in .github/actionlint.yaml can go" >&2
  exit 1
fi
name="${target#"$root"/}"

# Fed on stdin so a temp copy works without mounting anything. -stdin-filename
# only labels the output, nothing writes the file.
# shellcheck disable=SC2094
output="$(docker run --rm -i "$image" -config-file /dev/null -no-color -oneline \
  -stdin-filename "$name" - < "$target" 2>&1)"
rc=$?

# 0 is a clean lint and 1 is findings. Anything else, or 1 with nothing printed,
# means actionlint didn't really run, and that must not read as upstream support.
if [[ $rc -ne 0 && $rc -ne 1 ]] || [[ $rc -eq 1 && -z "$output" ]]; then
  echo "tripwire: actionlint didn't run on $name (rc=$rc), can't tell if the \$/ ignore is still needed" >&2
  [[ -n "$output" ]] && printf '%s\n' "$output" >&2
  exit 2
fi

if ! grep -Pq -- "$diagnostic" <<<"$output"; then
  echo "actionlint understands \`\$/\` now: drop the ignore in .github/actionlint.yaml (probed $name)" >&2
  [[ -n "$output" ]] && printf '%s\n' "$output" >&2
  exit 1
fi

echo "tripwire: actionlint still flags \$/ refs in $name (rc=$rc), the ignore stays"
exit 0
