"""Selftest for verify.py. Run: python3 -m unittest discover -s .github/actions/verify-pytest-shards"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from verify import check  # noqa: E402

MODULES = ["tests/m/a.py", "tests/b.py", "tests/c.py", "tests/d.py", "tests/e.py"]
SPLIT = {1: ["tests/m/a.py", "tests/c.py", "tests/e.py"], 2: ["tests/b.py", "tests/d.py"]}


class VerifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, index: int = 1, **overrides: object) -> None:
        report: dict[str, object] = {
            "schema": 1,
            "index": index,
            "count": 2,
            "modules": MODULES,
            "selected": SPLIT.get(index, []),
        }
        report.update(overrides)
        # download-artifact puts each artifact in its own folder.
        target = self.dir / name / "pytest-shard-report.json"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(report), encoding="utf-8")

    def good(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=2)

    def test_a_clean_split_passes(self) -> None:
        self.good()
        self.assertEqual(check(self.dir, 2), [])

    def test_no_reports_fails(self) -> None:
        self.assertIn("found 0", check(self.dir, 2)[0])

    def test_a_missing_shard_fails(self) -> None:
        self.write("r1", index=1)
        self.assertIn("found 1", check(self.dir, 2)[0])

    def test_the_same_index_twice_fails(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=1)
        self.assertTrue(any("indexes" in p for p in check(self.dir, 2)))

    def test_a_shard_run_with_another_count_fails(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=2, count=3)
        self.assertTrue(any("1 of 3" in p for p in check(self.dir, 2)))

    def test_a_module_in_two_shards_fails(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=2, selected=["tests/b.py", "tests/d.py", "tests/e.py"])
        self.assertTrue(any("tests/e.py ran in shards 1 and 2" in p for p in check(self.dir, 2)))

    def test_a_module_in_no_shard_fails(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=2, selected=["tests/b.py"])
        self.assertTrue(
            any("1 modules ran in no shard" in p and "tests/d.py" in p for p in check(self.dir, 2))
        )

    def test_different_collections_fail(self) -> None:
        self.write("r1", index=1)
        self.write("r2", index=2, modules=MODULES[:-1])
        self.assertTrue(any("different module list" in p for p in check(self.dir, 2)))

    def test_a_selected_module_nobody_collected_fails(self) -> None:
        self.write("r1", index=1, selected=[*SPLIT[1], "tests/ghost.py"])
        self.write("r2", index=2)
        self.assertTrue(any("tests/ghost.py" in p for p in check(self.dir, 2)))

    def test_an_unknown_schema_fails(self) -> None:
        self.write("r1", index=1, schema=2)
        self.write("r2", index=2)
        self.assertTrue(any("schema 1" in p for p in check(self.dir, 2)))

    def test_a_malformed_report_fails(self) -> None:
        self.write("r1", index=1, modules="tests/a.py")
        self.write("r2", index=2)
        self.assertTrue(any("schema 1" in p for p in check(self.dir, 2)))

    def test_unreadable_json_fails(self) -> None:
        self.good()
        (self.dir / "r1" / "pytest-shard-report.json").write_text("{", encoding="utf-8")
        self.assertTrue(any("unreadable" in p for p in check(self.dir, 2)))


if __name__ == "__main__":
    unittest.main()
