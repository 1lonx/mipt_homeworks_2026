#!/usr/bin/env python

import sys
from collections.abc import Generator
from typing import Any, cast

# Type aliases to reduce complexity in function signatures
Transaction = dict[str, Any]
CostDict = dict[str, float]

UNKNOWN_COMMAND_MSG = "Unknown command!"
NONPOSITIVE_VALUE_MSG = "Value must be grater than zero!"
INCORRECT_DATE_MSG = "Invalid date!"
NOT_EXISTS_CATEGORY = "Category not exists!"
OP_SUCCESS_MSG = "Added"

DATE_PARTS = 3
MONTH_MAX = 12
CATEGORY_PARTS = 2
FEBRUARY = 2
FEB_LEAP_DAYS = 29

KEY_TYPE = "type"
KEY_AMOUNT = "amount"
KEY_DATE = "date"
KEY_CATEGORY = "category"

VALUE_INCOME = "income"
VALUE_COST = "cost"

INCOME_ARGS = 3
COST_ARGS = 4
COST_CATEGORIES_ARGS = 2
MIN_COST_ARGS = 2
STATS_ARGS = 2

DAYS_IN_MONTH = [
    31,
    28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
]

EXPENSE_CATEGORIES = {
    "Food": ("Supermarket", "Restaurants", "FastFood", "Coffee", "Delivery"),
    "Transport": ("Taxi", "Public transport", "Gas", "Car service"),
    "Housing": ("Rent", "Utilities", "Repairs", "Furniture"),
    "Health": ("Pharmacy", "Doctors", "Dentist", "Lab tests"),
    "Entertainment": ("Movies", "Concerts", "Games", "Subscriptions"),
    "Clothing": ("Outerwear", "Casual", "Shoes", "Accessories"),
    "Education": ("Courses", "Books", "Tutors"),
    "Communications": ("Mobile", "Internet", "Subscriptions"),
    "Other": ("SomeCategory", "SomeOtherCategory"),
}

financial_transactions_storage: list[Transaction] = []


def is_leap_year(year: int) -> bool:
    if year % 4 != 0:
        return False
    if year % 100 == 0:
        return year % 400 == 0
    return True


def extract_date(maybe_dt: str) -> tuple[int, int, int] | None:
    parts = maybe_dt.split("-")
    if len(parts) != DATE_PARTS:
        return None
    if not all(p.isdigit() for p in parts):
        return None
    d, m, y = map(int, parts)
    if not (1 <= m <= MONTH_MAX):
        return None
    if m == FEBRUARY and is_leap_year(y):
        ok = 1 <= d <= FEB_LEAP_DAYS
    else:
        ok = 1 <= d <= DAYS_IN_MONTH[m - 1]
    return (d, m, y) if ok else None


def _is_valid_category(cat: str) -> bool:
    parts = cat.split("::")
    if len(parts) != CATEGORY_PARTS:
        return False
    common, target = parts
    return common in EXPENSE_CATEGORIES and target in EXPENSE_CATEGORIES[common]


def income_handler(amount: float, income_date: str) -> str:
    if amount <= 0:
        financial_transactions_storage.append({})
        return NONPOSITIVE_VALUE_MSG
    date_tup = extract_date(income_date)
    if date_tup is None:
        financial_transactions_storage.append({})
        return INCORRECT_DATE_MSG
    financial_transactions_storage.append(
        {
            KEY_TYPE: VALUE_INCOME,
            KEY_AMOUNT: amount,
            KEY_DATE: date_tup,
        }
    )
    return OP_SUCCESS_MSG


def cost_handler(category_name: str, amount: float, income_date: str) -> str:
    if amount <= 0:
        financial_transactions_storage.append({})
        return NONPOSITIVE_VALUE_MSG
    date_tup = extract_date(income_date)
    if date_tup is None:
        financial_transactions_storage.append({})
        return INCORRECT_DATE_MSG
    if not _is_valid_category(category_name):
        financial_transactions_storage.append({})
        return NOT_EXISTS_CATEGORY
    financial_transactions_storage.append(
        {
            KEY_TYPE: VALUE_COST,
            KEY_AMOUNT: amount,
            KEY_DATE: date_tup,
            KEY_CATEGORY: category_name,
        }
    )
    return OP_SUCCESS_MSG


def cost_categories_handler() -> str:
    lines: list[str] = []
    for common, targets in EXPENSE_CATEGORIES.items():
        lines.extend(f"{common}::{t}" for t in targets)
    return "\n".join(lines)


def _to_int(val: Any) -> int:
    return cast("int", val)


_INVALID_DATE_MSG = "Invalid date format in storage"


def _normalize_date(date_val: Any) -> tuple[int, int, int]:
    if isinstance(date_val, tuple) and len(date_val) == DATE_PARTS:
        d, m, y = date_val
        return (y, m, d)
    if isinstance(date_val, str):
        parts = date_val.split("-")
        if len(parts) != DATE_PARTS:
            raise ValueError(_INVALID_DATE_MSG)
        if not all(p.isdigit() for p in parts):
            raise ValueError(_INVALID_DATE_MSG)
        d, m, y = map(int, parts)
        return (y, m, d)
    raise ValueError(_INVALID_DATE_MSG)


def _transaction_date_le(t: Transaction, target: tuple[int, int, int]) -> bool:
    try:
        t_date = _normalize_date(t[KEY_DATE])
    except ValueError:
        return False
    return t_date <= target


def _filter_transactions_until(date_tup: tuple[int, int, int]) -> list[Transaction]:
    target = (date_tup[2], date_tup[1], date_tup[0])
    return [t for t in financial_transactions_storage if t and _transaction_date_le(t, target)]


def _same_month_year(t: Transaction, y: int, m: int) -> bool:
    try:
        ty, tm, _ = _normalize_date(t[KEY_DATE])
    except ValueError:
        return False
    return ty == y and tm == m


def _is_income(t: Transaction) -> bool:
    return t.get(KEY_TYPE) == VALUE_INCOME or KEY_CATEGORY not in t


def _is_cost(t: Transaction) -> bool:
    return t.get(KEY_TYPE) == VALUE_COST or KEY_CATEGORY in t


def _total_totals(trans: list[Transaction]) -> tuple[float, float]:
    total_expense = 0
    total_income = 0
    for t in trans:
        if _is_income(t):
            total_income += t[KEY_AMOUNT]
        elif _is_cost(t):
            total_expense += t[KEY_AMOUNT]
    return total_expense, total_income


def _aggregate_costs(trans: list[Transaction], y: int, m: int) -> CostDict:
    res: dict[str, float] = {}
    for t in trans:
        if not _is_cost(t):
            continue
        if not _same_month_year(t, y, m):
            continue
        cat = t[KEY_CATEGORY]
        res[cat] = res.get(cat, 0) + t[KEY_AMOUNT]
    return {k: round(v, 2) for k, v in res.items()}


def _cat_expenses_month(trans: list[Transaction], y: int, m: int) -> CostDict:
    return _aggregate_costs(trans, y, m)


def _fmt_amt(amt: float) -> str:
    return str(round(amt, 2))


def _format_stats_lines(
    date: str,
    total_expense_all: float,
    total_income_all: float,
    cat_exp_month: CostDict,
) -> list[str]:
    capital = total_expense_all - total_income_all
    profit_word = "profit" if capital >= 0 else "loss"

    lines = [
        f"Your statistics as of {date}:",
        f"Total capital: {_fmt_amt(capital)} rubles",
        f"This month, the {profit_word} amounted to {_fmt_amt(capital)} rubles.",
        f"Income: {_fmt_amt(total_expense_all)} rubles",
        f"Expenses: {_fmt_amt(total_income_all)} rubles",
        "",
        "Details (category: amount):",
    ]
    if cat_exp_month:
        for idx, (cat, amt) in enumerate(cat_exp_month.items()):
            lines.append(f"{idx}. {cat}: {_fmt_amt(amt)}")
    return lines


def _format_stats(
    date: str,
    total_expense_all: float,
    total_income_all: float,
    cat_exp_month: CostDict,
) -> str:
    return "\n".join([*_format_stats_lines(date, total_expense_all, total_income_all, cat_exp_month), ""])


def stats_handler(report_date: str) -> str:
    date_tup = extract_date(report_date)
    if date_tup is None:
        return INCORRECT_DATE_MSG
    relevant = _filter_transactions_until(date_tup)
    total_expense_all, total_income_all = _total_totals(relevant)
    cat_exp_month = _cat_expenses_month(relevant, date_tup[2], date_tup[1])
    return _format_stats(report_date, total_expense_all, total_income_all, cat_exp_month)


def _parse_amount(s: str) -> float | None:
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _handle_income(parts: list[str]) -> None:
    if len(parts) != INCOME_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    amount = _parse_amount(parts[1])
    if amount is None:
        print(UNKNOWN_COMMAND_MSG)
        return
    print(income_handler(amount, parts[2]))


def _handle_cost(parts: list[str]) -> None:
    if len(parts) < MIN_COST_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    if parts[1] == "categories":
        if len(parts) != COST_CATEGORIES_ARGS:
            print(UNKNOWN_COMMAND_MSG)
            return
        print(cost_categories_handler())
        return
    if len(parts) != COST_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    amount = _parse_amount(parts[2])
    if amount is None:
        print(UNKNOWN_COMMAND_MSG)
        return
    print(cost_handler(parts[1], amount, parts[3]))


def _handle_stats(parts: list[str]) -> None:
    if len(parts) != STATS_ARGS:
        print(UNKNOWN_COMMAND_MSG)
        return
    print(stats_handler(parts[1]))


def _read_lines() -> Generator[str]:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if line:
            yield line


COMMAND_HANDLERS = {
    "income": _handle_income,
    "cost": _handle_cost,
    "stats": _handle_stats,
}


def main() -> None:
    for line in _read_lines():
        parts = line.split()
        handler = COMMAND_HANDLERS.get(parts[0])
        if handler:
            handler(parts)
        else:
            print(UNKNOWN_COMMAND_MSG)


if __name__ == "__main__":
    main()
