"""
Core financial calculation logic. Kept free of Flask/request concerns so it
is easily unit-testable (see tests/test_finance_service.py).
"""
from datetime import date
from collections import defaultdict

from app.extensions import db
from app.models import Income, Expense, CategoryEnvelope
from app.models.expense import EXPENSE_CATEGORIES
from app.services.budget_rules import classify_utilization, STATUS_LABELS


def month_bounds(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def get_totals(user_id: int, year: int = None, month: int = None):
    """Total inflows, outflows, net cash flow, savings rate for a given month
    (defaults to the current month)."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    start, end = month_bounds(year, month)

    incomes = Income.query.filter(
        Income.user_id == user_id, Income.date >= start, Income.date < end
    ).all()
    expenses = Expense.query.filter(
        Expense.user_id == user_id, Expense.date >= start, Expense.date < end
    ).all()

    total_inflow = sum(i.amount for i in incomes)
    total_outflow = sum(e.amount for e in expenses)
    net_cash_flow = total_inflow - total_outflow
    savings_rate = savings_rate_pct(total_inflow, total_outflow)

    return {
        "total_inflow": round(total_inflow, 2),
        "total_outflow": round(total_outflow, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "savings_rate": savings_rate,
        "year": year,
        "month": month,
    }


def savings_rate_pct(total_inflow: float, total_outflow: float) -> float:
    """Savings Rate % = (Inflow - Outflow) / Inflow * 100, clamped at 0 when inflow is 0."""
    if total_inflow <= 0:
        return 0.0
    return round(((total_inflow - total_outflow) / total_inflow) * 100, 1)


def category_breakdown(user_id: int, year: int = None, month: int = None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    start, end = month_bounds(year, month)

    expenses = Expense.query.filter(
        Expense.user_id == user_id, Expense.date >= start, Expense.date < end
    ).all()

    totals = defaultdict(float)
    for e in expenses:
        totals[e.category] += e.amount

    grand_total = sum(totals.values()) or 1.0
    breakdown = []
    for cat in EXPENSE_CATEGORIES:
        amt = round(totals.get(cat, 0.0), 2)
        pct = round((amt / grand_total) * 100, 1) if grand_total else 0.0
        breakdown.append({"category": cat, "amount": amt, "pct": pct})
    return breakdown


def envelope_status(user_id: int, year: int = None, month: int = None):
    """Per-category envelope utilization using budget_rules thresholds."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    start, end = month_bounds(year, month)

    envelopes = {e.category: e.limit_amount for e in CategoryEnvelope.query.filter_by(user_id=user_id).all()}
    expenses = Expense.query.filter(
        Expense.user_id == user_id, Expense.date >= start, Expense.date < end
    ).all()
    spent = defaultdict(float)
    for e in expenses:
        spent[e.category] += e.amount

    results = []
    for cat in EXPENSE_CATEGORIES:
        limit = envelopes.get(cat, 0.0)
        amt = round(spent.get(cat, 0.0), 2)
        pct = round((amt / limit) * 100, 1) if limit > 0 else (100.0 if amt > 0 else 0.0)
        status = classify_utilization(pct)
        results.append({
            "category": cat,
            "spent": amt,
            "limit": limit,
            "utilization_pct": pct,
            "status": status,
            "status_label": STATUS_LABELS[status],
        })
    return results


def overall_burn(user_id: int, monthly_cap: float, year: int = None, month: int = None):
    totals = get_totals(user_id, year, month)
    spent = totals["total_outflow"]
    pct = round((spent / monthly_cap) * 100, 1) if monthly_cap > 0 else 0.0
    status = classify_utilization(pct)
    return {
        "spent": spent,
        "cap": monthly_cap,
        "utilization_pct": pct,
        "status": status,
        "status_label": STATUS_LABELS[status],
    }


def recent_transactions(user_id: int, limit: int = 10):
    incomes = Income.query.filter_by(user_id=user_id).order_by(Income.date.desc(), Income.id.desc()).limit(limit).all()
    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc(), Expense.id.desc()).limit(limit).all()

    merged = [
        {**i.to_dict(), "type": "income"} for i in incomes
    ] + [
        {**e.to_dict(), "type": "expense"} for e in expenses
    ]
    merged.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return merged[:limit]
