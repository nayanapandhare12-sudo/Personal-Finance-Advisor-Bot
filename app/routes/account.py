from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Income, Expense, CategoryEnvelope, SavingsGoal
from app.routes.dashboard import current_user
from app.services.budget_rules import CURRENCIES
from app.services.seed import reset_demo_data

account_bp = Blueprint("account", __name__)


@account_bp.route("/currency", methods=["PUT"])
def set_currency():
    user = current_user()
    data = request.get_json(force=True) or {}
    code = data.get("currency")
    if code not in CURRENCIES:
        return jsonify({"errors": [f"currency must be one of {list(CURRENCIES.keys())}"]}), 400
    user.currency = code
    db.session.commit()
    return jsonify({"currency": user.currency, "rates": CURRENCIES})


@account_bp.route("/currencies", methods=["GET"])
def list_currencies():
    return jsonify(CURRENCIES)


@account_bp.route("/export", methods=["GET"])
def export_data():
    user = current_user()
    payload = {
        "user": user.to_dict(),
        "incomes": [i.to_dict() for i in Income.query.filter_by(user_id=user.id).all()],
        "expenses": [e.to_dict() for e in Expense.query.filter_by(user_id=user.id).all()],
        "envelopes": [e.to_dict() for e in CategoryEnvelope.query.filter_by(user_id=user.id).all()],
        "goals": [g.to_dict() for g in SavingsGoal.query.filter_by(user_id=user.id).all()],
    }
    return jsonify(payload)


@account_bp.route("/reset-demo", methods=["POST"])
def reset_demo():
    user = current_user()
    reset_demo_data(user)
    return jsonify({"status": "reset", "user": user.to_dict()})
