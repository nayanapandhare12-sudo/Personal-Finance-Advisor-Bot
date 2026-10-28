from datetime import datetime
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import SavingsGoal
from app.routes.dashboard import current_user

goals_bp = Blueprint("goals", __name__)


@goals_bp.route("", methods=["GET"])
def list_goals():
    user = current_user()
    items = SavingsGoal.query.filter_by(user_id=user.id).order_by(SavingsGoal.deadline.asc()).all()
    return jsonify([g.to_dict() for g in items])


@goals_bp.route("", methods=["POST"])
def create_goal():
    user = current_user()
    data = request.get_json(force=True) or {}
    errors = []
    name = (data.get("name") or "").strip()
    if not name:
        errors.append("Goal name is required.")
    try:
        target_amount = float(data.get("target_amount"))
        if target_amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        target_amount = None
        errors.append("target_amount must be a positive number.")
    try:
        current_amount = float(data.get("current_amount", 0))
        if current_amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        current_amount = 0.0
        errors.append("current_amount must be a non-negative number.")
    try:
        deadline = datetime.strptime(data.get("deadline"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        deadline = None
        errors.append("deadline must be in YYYY-MM-DD format.")

    if errors:
        return jsonify({"errors": errors}), 400

    goal = SavingsGoal(
        user_id=user.id, name=name, target_amount=target_amount,
        current_amount=current_amount, deadline=deadline,
        completed=current_amount >= target_amount,
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(goal.to_dict()), 201


@goals_bp.route("/<int:goal_id>/deposit", methods=["POST"])
def deposit(goal_id):
    user = current_user()
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first_or_404()
    data = request.get_json(force=True) or {}
    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"errors": ["amount must be a positive number."]}), 400

    goal.current_amount = round(goal.current_amount + amount, 2)
    if goal.current_amount >= goal.target_amount:
        goal.completed = True
    db.session.commit()
    return jsonify(goal.to_dict())


@goals_bp.route("/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    user = current_user()
    goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"deleted": goal_id})
