from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import CategoryEnvelope
from app.models.expense import EXPENSE_CATEGORIES
from app.routes.dashboard import current_user
from app.services import finance_service

budget_bp = Blueprint("budget", __name__)


@budget_bp.route("/cap", methods=["GET"])
def get_cap():
    user = current_user()
    return jsonify({"monthly_spending_cap": user.monthly_spending_cap})


@budget_bp.route("/cap", methods=["PUT"])
def set_cap():
    user = current_user()
    data = request.get_json(force=True) or {}
    try:
        cap = float(data.get("monthly_spending_cap"))
        if cap <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"errors": ["monthly_spending_cap must be a positive number."]}), 400
    user.monthly_spending_cap = cap
    db.session.commit()
    return jsonify({"monthly_spending_cap": user.monthly_spending_cap})


@budget_bp.route("/envelopes", methods=["GET"])
def list_envelopes():
    user = current_user()
    return jsonify(finance_service.envelope_status(user.id))


@budget_bp.route("/envelopes", methods=["PUT"])
def upsert_envelope():
    user = current_user()
    data = request.get_json(force=True) or {}
    category = data.get("category")
    if category not in EXPENSE_CATEGORIES:
        return jsonify({"errors": [f"Category must be one of {EXPENSE_CATEGORIES}."]}), 400
    try:
        limit_amount = float(data.get("limit_amount"))
        if limit_amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"errors": ["limit_amount must be a non-negative number."]}), 400

    envelope = CategoryEnvelope.query.filter_by(user_id=user.id, category=category).first()
    if envelope:
        envelope.limit_amount = limit_amount
    else:
        envelope = CategoryEnvelope(user_id=user.id, category=category, limit_amount=limit_amount)
        db.session.add(envelope)
    db.session.commit()
    return jsonify(envelope.to_dict())
