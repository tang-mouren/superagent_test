"""Run with: python3 -m unittest -v."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ledger import add_entry, load_entries, main, parse_amount, summarize


class LedgerTests(unittest.TestCase):
    def test_amount_uses_integer_cents(self):
        self.assertEqual(parse_amount("12.50"), 1250)
        self.assertEqual(parse_amount("0.01"), 1)
        self.assertEqual(parse_amount("0.10") + parse_amount("0.20"), 30)

    def test_reject_invalid_amounts(self):
        for amount in ("0", "-1", "1.001", "abc", "NaN", "Infinity"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                parse_amount(amount)

    def test_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_entries(Path(folder) / "missing.json"), [])

    def test_add_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "expenses.json"
            add_entry(path, "12.50", "餐饮", "2026-11-01", "午饭")
            add_entry(path, "2", "交通", "2026-11-02", "地铁")
            entries = load_entries(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["cents"], 1250)
            self.assertEqual(entries[0]["note"], "午饭")
            self.assertEqual(summarize(entries)["交通"], 200)

    def test_invalid_date_does_not_change_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            add_entry(path, "5", "其他", "2026-11-01", "已有记录")
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                add_entry(path, "8", "餐饮", "2026-02-30", "错误日期")
            self.assertEqual(path.read_bytes(), before)

    def test_corrupt_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text("not JSON", encoding="utf-8")
            with self.assertRaises(ValueError):
                add_entry(path, "1", "其他", "2026-11-01", "")
            self.assertEqual(path.read_text(encoding="utf-8"), "not JSON")

    def test_summary_includes_empty_categories(self):
        totals = summarize([{"category": "学习", "cents": 3500}])
        self.assertEqual(totals, {"餐饮": 0, "交通": 0, "学习": 3500, "其他": 0})

    def test_cli_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"}
            ]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "summary"]), 0)
            self.assertIn("合计：12.50 元", output.getvalue())


if __name__ == "__main__":
    unittest.main()
