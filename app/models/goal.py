from datetime import date, datetime
from app.extensions import db


class SavingsGoal(db.Model):
    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    deadline = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def remaining_days(self):
        delta = self.deadline - date.today()
        return max(delta.days, 0)

    def progress_pct(self):
        if self.target_amount <= 0:
            return 0.0
        return min(round((self.current_amount / self.target_amount) * 100, 1), 100.0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "deadline": self.deadline.isoformat(),
            "completed": self.completed,
            "remaining_days": self.remaining_days(),
            "progress_pct": self.progress_pct(),
        }
