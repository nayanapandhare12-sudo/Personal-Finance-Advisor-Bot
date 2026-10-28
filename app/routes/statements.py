from datetime import date
from flask import Blueprint, render_template, request

from app.models import Expense, Income
from app.routes.dashboard import current_user
from app.services import finance_service

statements_bp = Blueprint("statements", __name__)


@statements_bp.route("/statements")
def statements():
    user = current_user()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    totals = finance_service.get_totals(user.id, year, month)
    breakdown = finance_service.category_breakdown(user.id, year, month)
    start, end = finance_service.month_bounds(year, month)

    incomes = Income.query.filter(
        Income.user_id == user.id, Income.date >= start, Income.date < end
    ).order_by(Income.date.asc()).all()
    expenses = Expense.query.filter(
        Expense.user_id == user.id, Expense.date >= start, Expense.date < end
    ).order_by(Expense.date.asc()).all()

    transactions = sorted(
        [{**i.to_dict(), "type": "Income"} for i in incomes]
        + [{**e.to_dict(), "type": "Expense"} for e in expenses],
        key=lambda x: x["date"],
    )

    return render_template(
        "statement.html",
        user=user, year=year, month=month, totals=totals,
        breakdown=breakdown, transactions=transactions,
    )
