"""Tests for check_suite.py's own-action check, against a throwaway repo layout."""

import os
import tempfile
import textwrap
import unittest
from pathlib import Path

import check_suite

ACTION = """\
name: A
inputs:
  reports-dir:
    required: true
  count:
    required: true
  note:
    required: false
runs:
  using: composite
  steps: []
"""


def workflow(uses: str, with_: str) -> str:
    head = "on: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n"
    step = f"      - uses: {uses}\n        with:\n"
    return head + step + textwrap.indent(with_, " " * 10) + "\n"


class ActionRefs(unittest.TestCase):
    def setUp(self) -> None:
        self.cwd = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        Path(".github/workflows").mkdir(parents=True)
        Path(".github/actions/a").mkdir(parents=True)
        Path(".github/actions/a/action.yml").write_text(ACTION, encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def problems(self, uses: str, with_: str) -> list[str]:
        Path(".github/workflows/w.yml").write_text(
            workflow(uses, with_), encoding="utf-8"
        )
        return check_suite.check_action_refs()

    def test_dollar_slash_with_its_inputs_passes(self) -> None:
        self.assertEqual(
            self.problems("$/.github/actions/a", "reports-dir: r\ncount: 2"), []
        )

    def test_tag_ref_is_refused(self) -> None:
        found = self.problems(
            "homelabforge/shared-workflows/.github/actions/a@v1.7.0",
            "reports-dir: r\ncount: 2",
        )
        self.assertEqual(len(found), 1)
        self.assertIn("has to be $/", found[0])

    def test_misspelled_action_path(self) -> None:
        found = self.problems("$/.github/actions/b", "reports-dir: r\ncount: 2")
        self.assertEqual(len(found), 1)
        self.assertIn("no .github/actions/b/action.yml", found[0])

    def test_input_the_action_does_not_take(self) -> None:
        found = self.problems(
            "$/.github/actions/a", "reports-dir: r\ncount: 2\nreport-dir: r"
        )
        self.assertEqual(len(found), 1)
        self.assertIn("report-dir", found[0])

    def test_required_input_left_out(self) -> None:
        found = self.problems("$/.github/actions/a", "reports-dir: r")
        self.assertEqual(len(found), 1)
        self.assertIn("count", found[0])


if __name__ == "__main__":
    unittest.main()
