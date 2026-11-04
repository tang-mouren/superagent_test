"""Run with: python3 -m unittest -v."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ledger import add_entry, filter_by_month, load_entries, main, parse_amount, summarize, validate_month


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

    def test_validate_month(self):
        self.assertEqual(validate_month("2026-11"), "2026-11")
        self.assertEqual(validate_month("2026-02"), "2026-02")
        for month in ("2026-13", "2026-1", "2026-00", "2026-11-01", "abc", "2026-02-30"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                validate_month(month)

    def test_filter_by_month(self):
        entries = [
            {"date": "2026-10-30", "category": "餐饮", "cents": 1800, "note": "晚饭"},
            {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"},
            {"date": "2025-11-01", "category": "其他", "cents": 100, "note": "去年同月"},
            {"date": "2026-12-01", "category": "交通", "cents": 400, "note": "地铁"},
        ]
        self.assertEqual(filter_by_month(entries, "2026-11"), entries[1:2])
        self.assertEqual(filter_by_month(entries, "2026-01"), [])

    def test_cli_summary_month(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--file", "examples/expenses.json", "summary", "--month", "2026-11"]), 0)
        self.assertIn("合计：22.50 元", output.getvalue())

    def test_cli_list_month_excludes_other_months(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--file", "examples/expenses.json", "list", "--month", "2026-11"]), 0)
        text = output.getvalue()
        self.assertIn("2026-11-01", text)
        self.assertNotIn("2026-10-30", text)
        self.assertNotIn("2025-11", text)

    def test_cli_month_without_records(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"}
            ]), encoding="utf-8")
            listing = io.StringIO()
            with contextlib.redirect_stdout(listing):
                self.assertEqual(main(["--file", str(path), "list", "--month", "2026-12"]), 0)
            self.assertIn("暂无支出", listing.getvalue())
            summary = io.StringIO()
            with contextlib.redirect_stdout(summary):
                self.assertEqual(main(["--file", str(path), "summary", "--month", "2026-12"]), 0)
            self.assertIn("合计：0.00 元", summary.getvalue())

    def test_cli_invalid_month_fails_without_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"}
            ]), encoding="utf-8")
            before = path.read_bytes()
            for month in ("2026-13", "2026-1"):
                with self.subTest(month=month), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        main(["--file", str(path), "summary", "--month", month])
            self.assertEqual(path.read_bytes(), before)

    def test_cli_summary_month_keeps_cross_year_same_month_apart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2025-12-31", "category": "餐饮", "cents": 500, "note": "去年十二月"},
                {"date": "2026-01-01", "category": "餐饮", "cents": 700, "note": "今年一月"},
            ]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "summary", "--month", "2025-12"]), 0)
            self.assertIn("合计：5.00 元", output.getvalue())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "summary", "--month", "2026-01"]), 0)
            self.assertIn("合计：7.00 元", output.getvalue())


if __name__ == "__main__":
    unittest.main()
