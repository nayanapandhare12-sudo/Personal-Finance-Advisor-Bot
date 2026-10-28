from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default="Alex Mercer")
    email = db.Column(db.String(200), unique=True, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    monthly_spending_cap = db.Column(db.Float, nullable=False, default=3000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    incomes = db.relationship("Income", backref="user", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="user", cascade="all, delete-orphan")
    envelopes = db.relationship("CategoryEnvelope", backref="user", cascade="all, delete-orphan")
    goals = db.relationship("SavingsGoal", backref="user", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", backref="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "currency": self.currency,
            "monthly_spending_cap": self.monthly_spending_cap,
        }
