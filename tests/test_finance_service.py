from app.services.finance_service import savings_rate_pct
from app.services.budget_rules import classify_utilization


def test_savings_rate_normal():
    assert savings_rate_pct(1000, 600) == 40.0


def test_savings_rate_zero_inflow():
    assert savings_rate_pct(0, 500) == 0.0


def test_savings_rate_overspend_negative():
    assert savings_rate_pct(1000, 1500) == -50.0


def test_classify_utilization_healthy():
    assert classify_utilization(0) == "healthy"
    assert classify_utilization(69.9) == "healthy"


def test_classify_utilization_moderate():
    assert classify_utilization(70) == "moderate"
    assert classify_utilization(89.9) == "moderate"


def test_classify_utilization_high():
    assert classify_utilization(90) == "high"
    assert classify_utilization(99.9) == "high"


def test_classify_utilization_critical():
    assert classify_utilization(100) == "critical"
    assert classify_utilization(150) == "critical"
