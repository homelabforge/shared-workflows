#!/usr/bin/env bash
# Tripwire for the `$/` ignore in .github/actionlint.yaml. Runs actionlint with
# no config, so the ignore is off, and fails once it stops flagging our `$/` ref.
# Usage: actionlint_ignore_tripwire.sh [workflow-file]
set -uo pipefail

image="${ACTIONLINT_IMAGE:-rhysd/actionlint@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667}"
workflow="${1:-.github/workflows/python-react-ci.yml}"
diagnostic='specifying action "\$/\.github/actions/[^"]+" in invalid format because ref is missing'

if [[ ! -f "$workflow" ]]; then
  echo "tripwire: $workflow not found" >&2
  exit 2
fi

# Fed on stdin so a temp copy works without mounting anything. -stdin-filename
# only labels the output, nothing writes the file.
# shellcheck disable=SC2094
output="$(docker run --rm -i "$image" -config-file /dev/null -no-color -oneline \
  -stdin-filename "$workflow" - < "$workflow" 2>&1)"
rc=$?

# 0 is a clean lint and 1 is findings. Anything else, or 1 with nothing printed,
# means actionlint didn't really run, and that must not read as upstream support.
if [[ $rc -ne 0 && $rc -ne 1 ]] || [[ $rc -eq 1 && -z "$output" ]]; then
  echo "tripwire: actionlint didn't run (rc=$rc), can't tell if the \$/ ignore is still needed" >&2
  [[ -n "$output" ]] && printf '%s\n' "$output" >&2
  exit 2
fi

if ! grep -Eq "$diagnostic" <<<"$output"; then
  echo "actionlint understands \`\$/\` now: drop the ignore in .github/actionlint.yaml" >&2
  [[ -n "$output" ]] && printf '%s\n' "$output" >&2
  exit 1
fi

echo "tripwire: actionlint still flags \$/ refs (rc=$rc), the ignore stays"
exit 0
