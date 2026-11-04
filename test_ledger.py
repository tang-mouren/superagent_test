"""Run with: python3 -m unittest -v."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ledger import add_entry, filter_month, load_entries, main, parse_amount, summarize


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

    def test_filter_month(self):
        entries = [
            {"date": "2026-10-31", "category": "学习", "cents": 3900, "note": "技术书"},
            {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"},
            {"date": "2026-12-25", "category": "交通", "cents": 400, "note": "地铁"},
        ]
        self.assertEqual(filter_month(entries, None), entries)
        month_entries = filter_month(entries, "2026-11")
        self.assertEqual(len(month_entries), 1)
        self.assertEqual(month_entries[0]["date"], "2026-11-01")

    def test_filter_month_rejects_invalid_month(self):
        entries = [{"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"}]
        for month in ("2026-13", "2026", "2026-1", "26-11", "abc"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                filter_month(entries, month)

    def test_cli_list_month(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2026-10-31", "category": "学习", "cents": 3900, "note": "技术书"},
                {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"},
                {"date": "2026-11-02", "category": "交通", "cents": 800, "note": "地铁"},
            ]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "list", "--month", "2026-11"]), 0)
            text = output.getvalue()
            self.assertNotIn("2026-10-31", text)
            self.assertIn("2026-11-01", text)
            self.assertIn("2026-11-02", text)

    def test_filter_month_cross_year_boundary(self):
        entries = [
            {"date": "2025-12-31", "category": "餐饮", "cents": 1800, "note": "跨年晚饭"},
            {"date": "2026-01-01", "category": "餐饮", "cents": 900, "note": "元旦"},
            {"date": "2026-12-31", "category": "交通", "cents": 400, "note": "跨年地铁"},
            {"date": "2027-01-02", "category": "交通", "cents": 500, "note": "新年地铁"},
        ]
        january = filter_month(entries, "2026-01")
        self.assertEqual([entry["date"] for entry in january], ["2026-01-01"])
        december = filter_month(entries, "2026-12")
        self.assertEqual([entry["date"] for entry in december], ["2026-12-31"])
        self.assertEqual(summarize(january)["餐饮"], 900)
        self.assertEqual(summarize(december)["交通"], 400)

    def test_cli_summary_month_total(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text(json.dumps([
                {"date": "2026-10-30", "category": "餐饮", "cents": 1800, "note": "晚饭"},
                {"date": "2026-10-31", "category": "学习", "cents": 3900, "note": "技术书"},
                {"date": "2026-11-01", "category": "餐饮", "cents": 1250, "note": "午饭"},
                {"date": "2026-11-02", "category": "交通", "cents": 400, "note": "地铁"},
                {"date": "2026-11-03", "category": "其他", "cents": 600, "note": "打印材料"},
            ]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "summary", "--month", "2026-11"]), 0)
            self.assertIn("合计：22.50 元", output.getvalue())
            self.assertNotIn("39.00", output.getvalue())

    def test_cli_summary_rejects_bad_month(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expenses.json"
            path.write_text("[]", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaises(SystemExit) as exited:
                    main(["--file", str(path), "summary", "--month", "2026-13"])
            self.assertEqual(exited.exception.code, 2)
            self.assertIn("月份格式不正确", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
