from datetime import datetime, date
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Expense
from app.models.expense import EXPENSE_CATEGORIES
from app.routes.dashboard import current_user

expense_bp = Blueprint("expense", __name__)


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
    if category not in EXPENSE_CATEGORIES:
        errors.append(f"Category must be one of {EXPENSE_CATEGORIES}.")

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


@expense_bp.route("", methods=["GET"])
def list_expenses():
    user = current_user()
    q = Expense.query.filter_by(user_id=user.id)
    category = request.args.get("category")
    search = request.args.get("search")
    start = request.args.get("start")
    end = request.args.get("end")
    if category:
        q = q.filter(Expense.category == category)
    if search:
        q = q.filter(Expense.description.ilike(f"%{search}%"))
    if start:
        q = q.filter(Expense.date >= datetime.strptime(start, "%Y-%m-%d").date())
    if end:
        q = q.filter(Expense.date <= datetime.strptime(end, "%Y-%m-%d").date())
    items = q.order_by(Expense.date.desc(), Expense.id.desc()).all()
    return jsonify([e.to_dict() for e in items])


@expense_bp.route("", methods=["POST"])
def create_expense():
    user = current_user()
    data = request.get_json(force=True) or {}
    errors, amount, category, parsed_date = _validate_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400
    item = Expense(
        user_id=user.id, amount=amount, category=category,
        description=data.get("description", ""), date=parsed_date,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@expense_bp.route("/<int:item_id>", methods=["DELETE"])
def delete_expense(item_id):
    user = current_user()
    item = Expense.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": item_id})


@expense_bp.route("/categories", methods=["GET"])
def categories():
    return jsonify(EXPENSE_CATEGORIES)
