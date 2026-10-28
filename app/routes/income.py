from datetime import datetime, date
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Income
from app.models.income import INCOME_CATEGORIES
from app.routes.dashboard import current_user

income_bp = Blueprint("income", __name__)


def _validate_payload(data):
    errors = []
    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            errors.append("Amount must be greater than 0.")
    except (TypeError, ValueError):
        amount = None
        errors.append("Amount must be a number.")

    category = data.get("category")
    if category not in INCOME_CATEGORIES:
        errors.append(f"Category must be one of {INCOME_CATEGORIES}.")

    date_str = data.get("date")
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Date must be in YYYY-MM-DD format.")
    else:
        parsed_date = date.today()

    return errors, amount, category, parsed_date


@income_bp.route("", methods=["GET"])
def list_incomes():
    user = current_user()
    q = Income.query.filter_by(user_id=user.id)
    category = request.args.get("category")
    search = request.args.get("search")
    start = request.args.get("start")
    end = request.args.get("end")
    if category:
        q = q.filter(Income.category == category)
    if search:
        q = q.filter(Income.description.ilike(f"%{search}%"))
    if start:
        q = q.filter(Income.date >= datetime.strptime(start, "%Y-%m-%d").date())
    if end:
        q = q.filter(Income.date <= datetime.strptime(end, "%Y-%m-%d").date())
    items = q.order_by(Income.date.desc(), Income.id.desc()).all()
    return jsonify([i.to_dict() for i in items])


@income_bp.route("", methods=["POST"])
def create_income():
    user = current_user()
    data = request.get_json(force=True) or {}
    errors, amount, category, parsed_date = _validate_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400
    item = Income(
        user_id=user.id, amount=amount, category=category,
        description=data.get("description", ""), date=parsed_date,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@income_bp.route("/<int:item_id>", methods=["DELETE"])
def delete_income(item_id):
    user = current_user()
    item = Income.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": item_id})


@income_bp.route("/categories", methods=["GET"])
def categories():
    return jsonify(INCOME_CATEGORIES)
