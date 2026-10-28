import random
from datetime import date, timedelta

from app.extensions import db
from app.models import User, Income, Expense, CategoryEnvelope, SavingsGoal, ChatMessage
from app.models.income import INCOME_CATEGORIES
from app.models.expense import EXPENSE_CATEGORIES

DEMO_EMAIL = "xyz@demo.local"

ENVELOPE_LIMITS = {
    "Housing": 1200,
    "Food & Dining": 500,
    "Transportation": 250,
    "Utilities": 200,
    "Healthcare": 150,
    "Entertainment": 150,
    "Shopping": 200,
    "Education": 100,
    "Personal Care": 100,
    "Miscellaneous": 100,
}


def _clear_user_data(user: User):
    Income.query.filter_by(user_id=user.id).delete()
    Expense.query.filter_by(user_id=user.id).delete()
    CategoryEnvelope.query.filter_by(user_id=user.id).delete()
    SavingsGoal.query.filter_by(user_id=user.id).delete()
    ChatMessage.query.filter_by(user_id=user.id).delete()
    db.session.commit()


def _populate_demo_data(user: User):
    today = date.today()
    rnd = random.Random(42)

    # Incomes for current + previous month
    for month_offset in (0, 1):
        month_date = today.replace(day=1) - timedelta(days=30 * month_offset)
        db.session.add(Income(
            user_id=user.id, amount=4200.0, category="Salary",
            description="Monthly salary", date=month_date.replace(day=1),
        ))
        db.session.add(Income(
            user_id=user.id, amount=rnd.randint(150, 600), category="Freelance",
            description="Freelance project", date=month_date.replace(day=min(15, 28)),
        ))
        db.session.add(Income(
            user_id=user.id, amount=rnd.randint(30, 120), category="Investments",
            description="Dividend payout", date=month_date.replace(day=min(20, 28)),
        ))

    # Expenses spread across the current month, deliberately breaching one category
    base_amounts = {
        "Housing": 1150,
        "Food & Dining": 610,   # over the 500 envelope -> Critical
        "Transportation": 210,
        "Utilities": 180,
        "Healthcare": 90,
        "Entertainment": 140,
        "Shopping": 175,
        "Education": 60,
        "Personal Care": 70,
        "Miscellaneous": 55,
    }
    for cat, total in base_amounts.items():
        splits = rnd.randint(2, 4)
        remaining = total
        for i in range(splits):
            chunk = round(remaining / (splits - i) * rnd.uniform(0.7, 1.3), 2)
            chunk = min(chunk, remaining)
            remaining = round(remaining - chunk, 2)
            day = rnd.randint(1, min(28, today.day if today.day > 3 else 15))
            db.session.add(Expense(
                user_id=user.id, amount=max(chunk, 1.0), category=cat,
                description=f"{cat} expense", date=today.replace(day=day),
            ))

    # Envelopes
    for cat, limit in ENVELOPE_LIMITS.items():
        db.session.add(CategoryEnvelope(user_id=user.id, category=cat, limit_amount=limit))

    # Savings goals
    db.session.add(SavingsGoal(
        user_id=user.id, name="Emergency Fund", target_amount=15000,
        current_amount=6400, deadline=today + timedelta(days=240),
    ))
    db.session.add(SavingsGoal(
        user_id=user.id, name="Japan Trip", target_amount=3500,
        current_amount=1200, deadline=today + timedelta(days=150),
    ))
    db.session.add(SavingsGoal(
        user_id=user.id, name="New Laptop", target_amount=1800,
        current_amount=1800, deadline=today + timedelta(days=10), completed=True,
    ))

    db.session.commit()


def ensure_demo_user():
    """Create (or fetch) the xyz demo account on first boot."""
    user = User.query.filter_by(email=DEMO_EMAIL).first()
    if user:
        return user
    user = User(
        name="XYZ", email=DEMO_EMAIL, currency="INR",
        monthly_spending_cap=3000.0,
    )
    db.session.add(user)
    db.session.commit()
    _populate_demo_data(user)
    return user


def reset_demo_data(user: User):
    _clear_user_data(user)
    _populate_demo_data(user)
