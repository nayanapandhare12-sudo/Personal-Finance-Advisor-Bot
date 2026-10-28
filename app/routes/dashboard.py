from flask import Blueprint, render_template, jsonify, current_app

from app.models import User
from app.services import finance_service
from app.models.expense import EXPENSE_CATEGORIES
from app.models.income import INCOME_CATEGORIES
from app.services.budget_rules import CURRENCIES

dashboard_bp = Blueprint("dashboard", __name__)


def current_user() -> User:
    return User.query.get(current_app.config["DEMO_USER_ID"])


@dashboard_bp.route("/")
def index():
    return render_template(
        "index.html",
        expense_categories=EXPENSE_CATEGORIES,
        income_categories=INCOME_CATEGORIES,
        currencies=CURRENCIES,
    )


@dashboard_bp.route("/api/dashboard/summary")
def summary():
    user = current_user()
    totals = finance_service.get_totals(user.id)
    burn = finance_service.overall_burn(user.id, user.monthly_spending_cap)
    breakdown = finance_service.category_breakdown(user.id)
    envelopes = finance_service.envelope_status(user.id)
    recent = finance_service.recent_transactions(user.id, limit=8)
    return jsonify({
        "user": user.to_dict(),
        "totals": totals,
        "burn": burn,
        "category_breakdown": breakdown,
        "envelopes": envelopes,
        "recent_transactions": recent,
    })
