#!/usr/bin/env python3
"""Fail unless the pytest shard reports cover every collected module exactly once.

Usage: verify.py REPORTS_DIR COUNT
"""

import json
import sys
from pathlib import Path

SCHEMA = 1


def _well_formed(data: object) -> bool:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return False
    lists_ok = all(
        isinstance(data.get(key), list) and all(isinstance(m, str) for m in data[key])
        for key in ("modules", "selected")
    )
    return (
        lists_ok
        and isinstance(data.get("index"), int)
        and isinstance(data.get("count"), int)
    )


def check(reports_dir: Path, count: int) -> list[str]:
    """Every problem with the reports. Empty means the shards add up."""
    files = sorted(reports_dir.rglob("*.json")) if reports_dir.is_dir() else []
    if len(files) != count:
        return [
            f"expected {count} shard reports, found {len(files)}: {[str(f) for f in files]}"
        ]

    problems: list[str] = []
    reports: list[tuple[Path, dict]] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path}: unreadable ({exc})")
            continue
        if not _well_formed(data):
            problems.append(f"{path}: not a schema {SCHEMA} shard report")
            continue
        reports.append((path, data))
    if problems:
        return problems

    indexes = sorted(data["index"] for _, data in reports)
    if indexes != list(range(1, count + 1)):
        problems.append(f"shard indexes {indexes}, expected 1..{count}")
    for path, data in reports:
        if data["count"] != count:
            problems.append(f"{path}: ran as 1 of {data['count']}, expected {count}")

    first_path, first = reports[0]
    modules = first["modules"]
    for path, data in reports[1:]:
        if data["modules"] != modules:
            problems.append(
                f"{path}: collected a different module list than {first_path}"
            )

    collected = set(modules)
    owner: dict[str, int] = {}
    for path, data in reports:
        for module in data["selected"]:
            if module not in collected:
                problems.append(
                    f"{path}: ran {module}, which the first shard never collected"
                )
            elif module in owner:
                problems.append(
                    f"{module} ran in shards {owner[module]} and {data['index']}"
                )
            else:
                owner[module] = data["index"]
    missing = [module for module in modules if module not in owner]
    if missing:
        problems.append(f"{len(missing)} modules ran in no shard, e.g. {missing[:5]}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    count = int(argv[2])
    problems = check(Path(argv[1]), count)
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        return 1
    modules = json.loads(
        sorted(Path(argv[1]).rglob("*.json"))[0].read_text(encoding="utf-8")
    )["modules"]
    print(f"OK: {count} shards ran each of {len(modules)} modules exactly once")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
