#!/usr/bin/env python3
"""Structure checks the YAML linter can't do.

1. Every input of _python-react-tests.yml is declared by both callers, with
   the same type and default, and passed straight through. Otherwise publish
   breaks on the next tag and nothing notices before then.
2. The jobs holding required-check names can't be skipped, and no other job
   uses those names. A skipped job reports Success to branch protection.
3. Steps call this repo's own actions through `$/`. A consumer that requires
   SHA-pinned actions refuses a tag ref, and `./` means the consumer's checkout.
   The action has to exist and get exactly the inputs it takes, since actionlint
   can't check a `$/` ref.
"""

import sys
from pathlib import Path

import yaml

WORKFLOWS = Path(".github/workflows")
ACTIONS = Path(".github/actions")
SUITE = "_python-react-tests.yml"
CALLERS = ("python-react-ci.yml", "python-react-publish.yml")
# keeper job id -> (required name, jobs it must wait for)
KEEPERS = {
    "_python-react-tests.yml": {
        "test-backend": ("Backend Tests", {"backend-checks", "backend-tests"}),
        "test-frontend": ("Frontend Tests", {"frontend-checks", "frontend-tests"}),
        "test-e2e": ("E2E Tests", {"e2e-tests"}),
    },
    "python-react-ci.yml": {
        "pg-migrations": ("PostgreSQL Migration Tests", {"pg-migrations-shard"}),
    },
}


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def call_inputs(workflow: dict) -> dict:
    # PyYAML reads a bare `on:` key as the boolean True.
    trigger = workflow.get("on", workflow.get(True))
    return trigger["workflow_call"]["inputs"]


def check_plumbing() -> list[str]:
    problems: list[str] = []
    suite_inputs = call_inputs(load(SUITE))
    for caller in CALLERS:
        workflow = load(caller)
        declared = call_inputs(workflow)
        calls = [
            job
            for job in workflow["jobs"].values()
            if SUITE in str(job.get("uses", ""))
        ]
        if len(calls) != 1:
            problems.append(
                f"{caller}: expected one job calling {SUITE}, found {len(calls)}"
            )
            continue
        passed = calls[0].get("with", {})
        for name, spec in suite_inputs.items():
            if name not in declared:
                problems.append(f"{caller}: doesn't declare input {name}")
            else:
                for key in ("type", "default"):
                    if declared[name].get(key) != spec.get(key):
                        problems.append(
                            f"{caller}: input {name} {key} is {declared[name].get(key)!r}, suite has {spec.get(key)!r}"
                        )
            if passed.get(name) != "${{ inputs." + name + " }}":
                problems.append(
                    f"{caller}: doesn't pass {name} through as ${{{{ inputs.{name} }}}}"
                )
        for name in passed:
            if name not in suite_inputs:
                problems.append(f"{caller}: passes {name}, which {SUITE} doesn't take")
    return problems


def check_keepers() -> list[str]:
    problems: list[str] = []
    for file, keepers in KEEPERS.items():
        jobs = load(file)["jobs"]
        required = {name for name, _ in keepers.values()}
        for job_id, (name, needs) in keepers.items():
            job = jobs.get(job_id)
            if job is None:
                problems.append(f"{file}: keeper job {job_id} is missing")
                continue
            if job.get("name") != name:
                problems.append(f"{file}: {job_id} must be named {name!r}")
            if not str(job.get("if", "")).startswith("always()"):
                problems.append(
                    f"{file}: {job_id} needs `if: always()...` or a skip reads as Success"
                )
            if set(job.get("needs", [])) != needs:
                problems.append(f"{file}: {job_id} must need exactly {sorted(needs)}")
        for job_id, job in jobs.items():
            if job_id not in keepers and job.get("name") in required:
                problems.append(
                    f"{file}: {job_id} reuses the required name {job.get('name')!r}"
                )
    return problems


def check_action_refs() -> list[str]:
    problems: list[str] = []
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(ACTIONS.glob("*/action.yml"))
    for path in files:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        steps = [
            s for job in doc.get("jobs", {}).values() for s in job.get("steps", [])
        ]
        steps += doc.get("runs", {}).get("steps", [])
        for step in steps:
            uses = str(step.get("uses", ""))
            if ".github/actions/" not in uses:
                continue
            if not uses.startswith("$/"):
                problems.append(f"{path}: {uses} has to be $/.github/actions/...")
                continue
            # actionlint can't follow `$/` and we mute it there, so check the
            # action exists and gets the inputs it takes here instead.
            action = Path(uses[2:]) / "action.yml"
            if not action.is_file():
                problems.append(f"{path}: {uses} has no {action}")
                continue
            doc_inputs = yaml.safe_load(action.read_text(encoding="utf-8"))
            inputs = doc_inputs.get("inputs") or {}
            passed = set(step.get("with") or {})
            for name in sorted(passed - set(inputs)):
                problems.append(f"{path}: {uses} doesn't take input {name}")
            for name, spec in inputs.items():
                spec = spec or {}
                if (
                    spec.get("required")
                    and "default" not in spec
                    and name not in passed
                ):
                    problems.append(f"{path}: {uses} needs input {name}")
    return problems


def main() -> int:
    problems = check_plumbing() + check_keepers() + check_action_refs()
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print(
            "OK: suite inputs plumbed through, keepers can't be skipped, own actions via $/"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
