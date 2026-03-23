#!/usr/bin/env python

from typing import Any, cast

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

DAYS_IN_MONTH = [
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31,
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

financial_transactions_storage: list[dict[str, Any]] = []


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
    ok = (
        1 <= d <= FEB_LEAP_DAYS
        if m == FEBRUARY and is_leap_year(y)
        else 1 <= d <= DAYS_IN_MONTH[m - 1]
    )
    return (d, m, y) if ok else None


def _is_valid_category(cat: str) -> bool:
    parts = cat.split("::")
    if len(parts) != CATEGORY_PARTS:
        return False
    common, target = parts
    return common in EXPENSE_CATEGORIES and target in EXPENSE_CATEGORIES[common]


def income_handler(amount: float, income_date: str) -> str:
    financial_transactions_storage.append({})
    if amount <= 0:
        return NONPOSITIVE_VALUE_MSG
    date_tup = extract_date(income_date)
    if date_tup is None:
        return INCORRECT_DATE_MSG
    financial_transactions_storage[-1] = {
        KEY_TYPE: "income",
        KEY_AMOUNT: amount,
        KEY_DATE: date_tup,
    }
    return OP_SUCCESS_MSG


def cost_handler(category_name: str, amount: float, income_date: str) -> str:
    financial_transactions_storage.append({})
    if amount <= 0:
        return NONPOSITIVE_VALUE_MSG
    date_tup = extract_date(income_date)
    if date_tup is None:
        return INCORRECT_DATE_MSG
    if not _is_valid_category(category_name):
        return NOT_EXISTS_CATEGORY
    financial_transactions_storage[-1] = {
        KEY_TYPE: "cost",
        KEY_AMOUNT: amount,
        KEY_DATE: date_tup,
        KEY_CATEGORY: category_name,
    }
    return OP_SUCCESS_MSG


def cost_categories_handler() -> str:
    lines: list[str] = []
    for common, targets in EXPENSE_CATEGORIES.items():
        lines.extend(f"{common}::{t}" for t in targets)
    return "\n".join(lines)


def _to_int(val: Any) -> int:
    return cast("int", val)


def _date_le(t: dict[str, Any], target: tuple[int, int, int]) -> bool:
    ty = _to_int(t[KEY_DATE][2])
    tm = _to_int(t[KEY_DATE][1])
    td = _to_int(t[KEY_DATE][0])
    return (ty, tm, td) <= target


def _filter_transactions_until(date_tup: tuple[int, int, int]) -> list[dict[str, Any]]:
    target = (date_tup[2], date_tup[1], date_tup[0])
    return [t for t in financial_transactions_storage if t and _date_le(t, target)]


def _same_month_year(t: dict[str, Any], y: int, m: int) -> bool:
    ty = _to_int(t[KEY_DATE][2])
    tm = _to_int(t[KEY_DATE][1])
    return ty == y and tm == m


def _month_aggregates(
    trans: list[dict[str, Any]], y: int, m: int
) -> tuple[float, float, float]:
    total = inc = exp = 0
    for t in trans:
        if t[KEY_TYPE] == "income":
            total += t[KEY_AMOUNT]
            if _same_month_year(t, y, m):
                inc += t[KEY_AMOUNT]
        else:
            total -= t[KEY_AMOUNT]
            if _same_month_year(t, y, m):
                exp += t[KEY_AMOUNT]
    return total, inc, exp


def _cat_expenses(
    trans: list[dict[str, Any]], y: int, m: int
) -> dict[str, float]:
    res: dict[str, float] = {}
    for t in trans:
        if t[KEY_TYPE] == "cost" and _same_month_year(t, y, m):
            cat = t[KEY_CATEGORY]
            res[cat] = res.get(cat, 0) + t[KEY_AMOUNT]
    return res


def _profit_line(inc: float, exp: float) -> str:
    profit = inc - exp
    word = "profit" if profit >= 0 else "loss"
    return f"This month, the {word} amounted to {abs(profit):.2f} rubles."


def _format_stats(
    date: str,
    agg: tuple[float, float, float],
    cat_exp: dict[str, float],
) -> str:
    lines = [
        f"Your statistics as of {date}:",
        f"Total capital: {agg[0]:.2f} rubles",
        _profit_line(agg[1], agg[2]),
        f"Income: {agg[1]:.2f} rubles",
        f"Expenses: {agg[2]:.2f} rubles",
        "Details (category: amount):",
    ]
    if cat_exp:
        for i, (cat, amt) in enumerate(sorted(cat_exp.items()), 1):
            lines.append(f"{i}. {cat}: {amt:.2f}")
    return "\n".join(lines)


def stats_handler(report_date: str) -> str:
    date_tup = extract_date(report_date)
    if date_tup is None:
        return INCORRECT_DATE_MSG
    relevant = _filter_transactions_until(date_tup)
    agg = _month_aggregates(relevant, date_tup[2], date_tup[1])
    cat_exp = _cat_expenses(relevant, date_tup[2], date_tup[1])
    return _format_stats(report_date, agg, cat_exp)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
