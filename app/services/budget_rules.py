"""
Single source of truth for budget status thresholds and related constants.
Used by the dashboard, envelope engine, and AI health audit so all three
always agree on what counts as Healthy / Moderate / High / Critical.
"""

# Utilization % thresholds (inclusive lower bound)
STATUS_HEALTHY_MAX = 70.0     # < 70%   -> Healthy
STATUS_MODERATE_MAX = 90.0    # 70-89%  -> Moderate
STATUS_HIGH_MAX = 100.0       # 90-99%  -> High
# >= 100% -> Critical (Breached)

STATUS_LABELS = {
    "healthy": "Healthy",
    "moderate": "Moderate",
    "high": "High",
    "critical": "Critical",
}

STATUS_COLORS = {
    "healthy": "#16a34a",   # green
    "moderate": "#2563eb",  # blue
    "high": "#ca8a04",      # amber
    "critical": "#dc2626",  # red
}

EMERGENCY_FUND_MONTHS_TARGET = 6

# Health score formula weights (must sum to 1.0)
HEALTH_SCORE_WEIGHTS = {
    "savings_rate": 0.4,
    "envelope_adherence": 0.35,
    "capital_reserves": 0.25,
}

GRADE_BANDS = [
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
]

CURRENCIES = {
    "INR": {"symbol": "\u20b9", "flag": "\U0001F1EE\U0001F1F3", "rate_per_usd": 83.0},
    "USD": {"symbol": "$", "flag": "\U0001F1FA\U0001F1F8", "rate_per_usd": 1.0},
    "EUR": {"symbol": "\u20ac", "flag": "\U0001F1EA\U0001F1FA", "rate_per_usd": 0.92},
    "GBP": {"symbol": "\u00a3", "flag": "\U0001F1EC\U0001F1E7", "rate_per_usd": 0.79},
    "JPY": {"symbol": "\u00a5", "flag": "\U0001F1EF\U0001F1F5", "rate_per_usd": 149.0},
    "CAD": {"symbol": "C$", "flag": "\U0001F1E8\U0001F1E6", "rate_per_usd": 1.36},
    "AUD": {"symbol": "A$", "flag": "\U0001F1E6\U0001F1FA", "rate_per_usd": 1.52},
    "KRW": {"symbol": "\u20a9", "flag": "\U0001F1F0\U0001F1F7", "rate_per_usd": 1330.0},
}


def classify_utilization(pct: float) -> str:
    """Map a utilization percentage to a status key."""
    if pct < STATUS_HEALTHY_MAX:
        return "healthy"
    if pct < STATUS_MODERATE_MAX:
        return "moderate"
    if pct < STATUS_HIGH_MAX:
        return "high"
    return "critical"


def grade_for_score(score: float) -> str:
    for threshold, grade in GRADE_BANDS:
        if score >= threshold:
            return grade
    return "F"
