from datetime import datetime
from app.extensions import db


class Budget(db.Model):
    """Overall monthly spending cap snapshot (kept for historical/audit purposes)."""
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    monthly_cap = db.Column(db.Float, nullable=False)
    effective_date = db.Column(db.Date, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "monthly_cap": self.monthly_cap,
            "effective_date": self.effective_date.isoformat(),
        }


class CategoryEnvelope(db.Model):
    __tablename__ = "category_envelopes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (db.UniqueConstraint("user_id", "category", name="uq_user_category"),)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "limit_amount": self.limit_amount,
        }
