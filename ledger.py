"""A small JSON-backed expense ledger using only Python's standard library."""

import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


CATEGORIES = ("餐饮", "交通", "学习", "其他")


def parse_amount(text):
    """Convert a positive amount with at most two decimal places into cents."""
    try:
        amount = Decimal(text)
        if not amount.is_finite() or amount <= 0:
            raise ValueError("金额必须是正数")
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise ValueError("金额最多保留两位小数")
        return int(cents)
    except InvalidOperation as exc:
        raise ValueError("金额格式不正确") from exc


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def load_entries(path):
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("账本格式错误：顶层必须是数组")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("账本格式错误：记录必须是对象")
        if type(entry.get("cents")) is not int or entry["cents"] <= 0:
            raise ValueError("账本格式错误：金额必须是正整数分")
        if entry.get("category") not in CATEGORIES:
            raise ValueError("账本格式错误：未知类别")
        if not isinstance(entry.get("note"), str):
            raise ValueError("账本格式错误：备注必须是文本")
        date.fromisoformat(entry["date"])
    return entries


def add_entry(path, amount, category, day, note):
    cents = parse_amount(amount)
    date.fromisoformat(day)
    if category not in CATEGORIES:
        raise ValueError("未知类别")
    entries = load_entries(path)
    entries.append({"date": day, "category": category, "cents": cents, "note": note})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def filter_month(entries, month):
    """Keep only entries dated in the given YYYY-MM month."""
    if month is None:
        return entries
    try:
        prefix = date.fromisoformat(month + "-01").strftime("%Y-%m")
    except ValueError as exc:
        raise ValueError("月份格式不正确，应为 YYYY-MM") from exc
    if not month.startswith(prefix):
        raise ValueError("月份格式不正确，应为 YYYY-MM")
    return [entry for entry in entries if entry["date"].startswith(prefix)]


def summarize(entries):
    totals = {category: 0 for category in CATEGORIES}
    for entry in entries:
        totals[entry["category"]] += entry["cents"]
    return totals


def main(argv=None):
    parser = argparse.ArgumentParser(description="小账本：记录支出，按类别汇总")
    parser.add_argument("--file", type=Path, default=Path("data/expenses.json"), help="账本 JSON 路径")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="添加一笔支出")
    add.add_argument("amount", help="金额，例如 12.50")
    add.add_argument("--category", choices=CATEGORIES, required=True)
    add.add_argument("--date", default=date.today().isoformat(), help="日期 YYYY-MM-DD")
    add.add_argument("--note", default="")
    for command_name, help_text in (("list", "查看支出"), ("summary", "按类别汇总支出")):
        command = commands.add_parser(command_name, help=help_text)
        command.add_argument("--month", default=None, metavar="YYYY-MM", help="只看指定月份，例如 2026-11")
    args = parser.parse_args(argv)
    try:
        if args.command == "add":
            add_entry(args.file, args.amount, args.category, args.date, args.note)
            print("已添加支出")
            return 0
        entries = filter_month(load_entries(args.file), args.month)
        if args.command == "list":
            print("日期       类别  金额（元）  备注")
            for entry in sorted(entries, key=lambda row: row["date"]):
                print(f"{entry['date']} {entry['category']}  {money(entry['cents']):>8}  {entry['note']}")
            if not entries:
                print("暂无支出")
        else:
            totals = summarize(entries)
            for category, cents in totals.items():
                print(f"{category}：{money(cents)} 元")
            print(f"合计：{money(sum(totals.values()))} 元")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"错误：{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
