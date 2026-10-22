import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_comments_blank_lines_and_ipv6(self):
        networks = build.parse("# Zoom\n3.7.35.0/25\n\n206.247.0.0/16  # media\n2620:123:2000::/40\n")
        self.assertEqual([str(n) for n in networks], ["3.7.35.0/25", "206.247.0.0/16", "2620:123:2000::/40"])

    def test_host_bits_are_cleared(self):
        self.assertEqual([str(n) for n in build.parse("3.235.96.27/31\n")], ["3.235.96.26/31"])

    def test_garbage_fails_the_build(self):
        for text in ("<html>blocked</html>\n", "0.0.0.0/0\n", "10.0.0.0/8\n", "\n# empty\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                build.parse(text)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def run_build(self, texts, previous=None):
        out = self.tmp / ("out" if previous is None else "out-next")
        return build.build(texts, previous, out), out

    def test_sources_are_merged_and_collapsed(self):
        changed, out = self.run_build(["206.247.0.0/17\n", "206.247.128.0/17\n3.7.35.0/25\n"])
        self.assertTrue(changed)
        ruleset = json.loads((out / "zoom-ip.json").read_text(encoding="utf-8"))
        self.assertEqual(ruleset, {"version": 2, "rules": [{"ip_cidr": ["3.7.35.0/25", "206.247.0.0/16"]}]})
        self.assertEqual((out / "zoom-ip.txt").read_text(encoding="utf-8"), "3.7.35.0/25\n206.247.0.0/16\n")

    def test_unchanged_list_is_not_published(self):
        _, out = self.run_build(["3.7.35.0/25\n"])
        changed, _ = self.run_build(["3.7.35.0/25\n"], previous=out)
        self.assertFalse(changed)

    def test_changes_are_reported(self):
        _, out = self.run_build(["3.7.35.0/25\n206.247.0.0/16\n"])
        changed, next_out = self.run_build(["206.247.0.0/16\n134.224.0.0/16\n"], previous=out)
        self.assertTrue(changed)
        report = (next_out / "CHANGES.md").read_text(encoding="utf-8")
        self.assertIn("2 подсетей (+1 / −1)", report)
        self.assertIn("добавлена `134.224.0.0/16`", report)
        self.assertIn("убрана `3.7.35.0/25`", report)

    def test_big_shrink_cancels_publication(self):
        _, out = self.run_build(["3.7.35.0/25\n134.224.0.0/16\n206.247.0.0/16\n"])
        with self.assertRaises(SystemExit):
            self.run_build(["3.7.35.0/25\n"], previous=out)


if __name__ == "__main__":
    unittest.main()
