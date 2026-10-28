from datetime import date

from app.extensions import db
from app.models import User, Expense, CategoryEnvelope
from app.services import finance_service


def test_envelope_status_classification(app, db):
    user = User(name="Budget Test", email="budget@test.local", currency="USD", monthly_spending_cap=1000)
    db.session.add(user)
    db.session.commit()

    db.session.add(CategoryEnvelope(user_id=user.id, category="Food & Dining", limit_amount=200))
    db.session.add(Expense(user_id=user.id, amount=250, category="Food & Dining", date=date.today()))
    db.session.commit()

    statuses = finance_service.envelope_status(user.id)
    food = next(s for s in statuses if s["category"] == "Food & Dining")
    assert food["status"] == "critical"
    assert food["utilization_pct"] == 125.0
