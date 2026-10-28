import os
import logging
from flask import Flask
from app.extensions import db
from app.config import get_config


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)

    logging.basicConfig(level=logging.INFO)

    from app.routes.dashboard import dashboard_bp
    from app.routes.income import income_bp
    from app.routes.expense import expense_bp
    from app.routes.budget import budget_bp
    from app.routes.goals import goals_bp
    from app.routes.advisor import advisor_bp
    from app.routes.statements import statements_bp
    from app.routes.account import account_bp
    from app.routes.viva import viva_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(income_bp, url_prefix="/api/income")
    app.register_blueprint(expense_bp, url_prefix="/api/expense")
    app.register_blueprint(budget_bp, url_prefix="/api/budget")
    app.register_blueprint(goals_bp, url_prefix="/api/goals")
    app.register_blueprint(advisor_bp, url_prefix="/api/advisor")
    app.register_blueprint(statements_bp)
    app.register_blueprint(account_bp, url_prefix="/api/account")
    app.register_blueprint(viva_bp)

    with app.app_context():
        db.create_all()
        from app.services.seed import ensure_demo_user
        ensure_demo_user()

    return app
