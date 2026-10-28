import logging
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import ChatMessage
from app.routes.dashboard import current_user
from app.services.advisor import get_advisor

logger = logging.getLogger(__name__)
advisor_bp = Blueprint("advisor", __name__)


@advisor_bp.route("/health-audit", methods=["GET"])
def health_audit():
    user = current_user()
    advisor = get_advisor()
    try:
        result = advisor.health_audit(user.id)
    except Exception as exc:  # noqa: BLE001 - absolute last-resort safety net
        logger.exception("Advisor health_audit crashed, using heuristic engine: %s", exc)
        from app.services.advisor import HeuristicAdvisor
        result = HeuristicAdvisor().health_audit(user.id)
    return jsonify(result)


@advisor_bp.route("/chat", methods=["POST"])
def chat():
    user = current_user()
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"errors": ["message is required."]}), 400

    history = [m.to_dict() for m in ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.id.asc()).all()]

    user_msg = ChatMessage(user_id=user.id, role="user", content=message, source="user")
    db.session.add(user_msg)
    db.session.commit()

    advisor = get_advisor()
    try:
        result = advisor.chat(user.id, message, history)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Advisor chat crashed, using heuristic engine: %s", exc)
        from app.services.advisor import HeuristicAdvisor
        result = HeuristicAdvisor().chat(user.id, message, history)

    assistant_msg = ChatMessage(
        user_id=user.id, role="assistant", content=result["reply"], source=result["source"],
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({"reply": result["reply"], "source": result["source"], "message_id": assistant_msg.id})


@advisor_bp.route("/chat/history", methods=["GET"])
def chat_history():
    user = current_user()
    items = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.id.asc()).all()
    return jsonify([m.to_dict() for m in items])


@advisor_bp.route("/chat/suggestions", methods=["GET"])
def chat_suggestions():
    return jsonify([
        "Am I overspending on dining?",
        "How can I hit my goal faster?",
        "What's my savings rate this month?",
        "Which category needs the most attention?",
    ])
