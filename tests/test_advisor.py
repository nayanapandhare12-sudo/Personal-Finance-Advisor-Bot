from app.services.budget_rules import grade_for_score
from app.services.advisor import compute_health_score, HeuristicAdvisor
from app.models import User
from app.extensions import db


def test_grade_bands():
    assert grade_for_score(95) == "A"
    assert grade_for_score(85) == "B"
    assert grade_for_score(75) == "C"
    assert grade_for_score(65) == "D"
    assert grade_for_score(40) == "F"


def test_compute_health_score_bounds():
    context = {
        "totals": {"savings_rate": 50, "total_outflow": 1000, "net_cash_flow": 500,
                    "total_inflow": 1500, "year": 2026, "month": 1},
        "envelopes": [
            {"category": "Food", "spent": 400, "limit": 500, "utilization_pct": 80, "status": "moderate", "status_label": "Moderate"},
        ],
    }
    result = compute_health_score(context)
    assert 0 <= result["score"] <= 100
    assert result["grade"] in {"A", "B", "C", "D", "F"}


def test_heuristic_advisor_health_audit_never_crashes(app, db):
    user = User(name="Test User", email="t@test.local", currency="USD", monthly_spending_cap=2000)
    db.session.add(user)
    db.session.commit()

    advisor = HeuristicAdvisor()
    result = advisor.health_audit(user.id)

    assert result["source"] == "heuristic"
    assert "score" in result
    assert "grade" in result
    assert len(result["action_plan"]) == 4


def test_heuristic_advisor_chat_grounded_in_zero_data(app, db):
    user = User(name="Empty User", email="empty@test.local", currency="USD", monthly_spending_cap=1000)
    db.session.add(user)
    db.session.commit()

    advisor = HeuristicAdvisor()
    result = advisor.chat(user.id, "What's my savings rate?", [])
    assert result["source"] == "heuristic"
    assert "0" in result["reply"] or "savings" in result["reply"].lower()
