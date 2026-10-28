"""
AI Financial Advisor layer.

Design: `AdvisorProvider` is the interface. `LLMAdvisor` calls the configured
Gemini model; `HeuristicAdvisor` computes the exact same shape of output with
pure formulas. `get_advisor()` returns an LLM-backed advisor when a key is
configured, but every LLM call is wrapped so that ANY failure (missing key,
network error, rate limit, malformed response) transparently falls back to
the heuristic engine. The app never crashes or shows a broken AI panel.
"""
import json
import logging
from abc import ABC, abstractmethod

from flask import current_app

from app.services import finance_service
from app.services.budget_rules import (
    grade_for_score,
    HEALTH_SCORE_WEIGHTS,
    EMERGENCY_FUND_MONTHS_TARGET,
)
from app.models import SavingsGoal

logger = logging.getLogger(__name__)


def build_financial_context(user_id: int) -> dict:
    """Assemble the real, live numbers the advisor is allowed to reason about.
    This is injected into every LLM prompt so the model cannot hallucinate
    figures, and is also what the heuristic engine computes from directly."""
    totals = finance_service.get_totals(user_id)
    breakdown = finance_service.category_breakdown(user_id)
    envelopes = finance_service.envelope_status(user_id)
    goals = [g.to_dict() for g in SavingsGoal.query.filter_by(user_id=user_id).all()]

    breached = [e for e in envelopes if e["status"] == "critical"]
    high = [e for e in envelopes if e["status"] == "high"]

    return {
        "totals": totals,
        "category_breakdown": breakdown,
        "envelopes": envelopes,
        "breached_categories": breached,
        "high_categories": high,
        "goals": goals,
    }


def compute_health_score(context: dict) -> dict:
    """
    Health Score (0-100) = weighted sum of three normalized sub-scores:
      - savings_rate_score: savings rate % clamped to [0,100]
      - envelope_adherence_score: 100 - avg(overage beyond 100% across breached envelopes),
        scaled by how many categories are within budget
      - capital_reserves_score: months of expenses covered by current net position,
        scaled against the 6-month emergency fund target

    Weights are defined centrally in budget_rules.HEALTH_SCORE_WEIGHTS.
    """
    totals = context["totals"]
    envelopes = context["envelopes"]

    # 1. Savings rate sub-score
    savings_rate_score = max(0.0, min(100.0, totals["savings_rate"]))

    # 2. Envelope adherence sub-score
    active_envelopes = [e for e in envelopes if e["limit"] > 0]
    if active_envelopes:
        per_cat_scores = []
        for e in active_envelopes:
            if e["utilization_pct"] <= 100:
                per_cat_scores.append(100 - (e["utilization_pct"] * 0.3))
            else:
                overage = e["utilization_pct"] - 100
                per_cat_scores.append(max(0.0, 70 - overage))
        envelope_adherence_score = sum(per_cat_scores) / len(per_cat_scores)
    else:
        envelope_adherence_score = 70.0  # neutral default when no envelopes configured

    # 3. Capital reserves sub-score (approximated via net cash flow vs avg monthly outflow)
    avg_monthly_outflow = totals["total_outflow"] or 1.0
    months_covered = max(totals["net_cash_flow"], 0) / avg_monthly_outflow
    capital_reserves_score = min(100.0, (months_covered / EMERGENCY_FUND_MONTHS_TARGET) * 100)

    weights = HEALTH_SCORE_WEIGHTS
    score = (
        savings_rate_score * weights["savings_rate"]
        + envelope_adherence_score * weights["envelope_adherence"]
        + capital_reserves_score * weights["capital_reserves"]
    )
    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "score": score,
        "grade": grade_for_score(score),
        "components": {
            "savings_rate_score": round(savings_rate_score, 1),
            "envelope_adherence_score": round(envelope_adherence_score, 1),
            "capital_reserves_score": round(capital_reserves_score, 1),
        },
    }


def emergency_liquidity_roadmap(context: dict) -> dict:
    totals = context["totals"]
    avg_monthly_outflow = totals["total_outflow"] or 0.0
    target_reserve = avg_monthly_outflow * EMERGENCY_FUND_MONTHS_TARGET
    current_reserve = max(totals["net_cash_flow"], 0.0)
    months_covered = round(current_reserve / avg_monthly_outflow, 1) if avg_monthly_outflow else 0.0
    gap = max(target_reserve - current_reserve, 0.0)
    # Suggest closing the gap over 12 months
    suggested_monthly_allocation = round(gap / 12, 2) if gap > 0 else 0.0

    return {
        "target_months": EMERGENCY_FUND_MONTHS_TARGET,
        "target_reserve": round(target_reserve, 2),
        "current_reserve": round(current_reserve, 2),
        "months_covered": months_covered,
        "gap": round(gap, 2),
        "suggested_monthly_allocation": suggested_monthly_allocation,
    }


def detect_anomalies(context: dict) -> list:
    anomalies = []
    for e in context["breached_categories"]:
        anomalies.append(
            f"{e['category']} is over budget: spent {e['spent']} against a limit of {e['limit']} "
            f"({e['utilization_pct']}% utilization)."
        )
    for e in context["high_categories"]:
        anomalies.append(
            f"{e['category']} is approaching its limit at {e['utilization_pct']}% utilization."
        )
    if context["totals"]["savings_rate"] < 10:
        anomalies.append(
            f"Savings rate is low at {context['totals']['savings_rate']}% this month."
        )
    return anomalies


def build_action_plan(context: dict, roadmap: dict) -> list:
    plan = []
    if context["breached_categories"]:
        worst = max(context["breached_categories"], key=lambda e: e["utilization_pct"])
        plan.append(
            f"Cut spending in {worst['category']} immediately — it's at "
            f"{worst['utilization_pct']}% of its envelope this month."
        )
    if roadmap["gap"] > 0:
        plan.append(
            f"Route an extra {roadmap['suggested_monthly_allocation']} per month toward your "
            f"emergency fund to close the {roadmap['gap']} reserve gap within a year."
        )
    if context["totals"]["savings_rate"] < 20:
        plan.append(
            "Automate a transfer of at least 20% of inflow to savings on payday "
            "before discretionary spending happens."
        )
    active_goals = [g for g in context["goals"] if not g["completed"]]
    if active_goals:
        nearest = min(active_goals, key=lambda g: g["remaining_days"])
        plan.append(
            f"Prioritize contributions to '{nearest['name']}' — {nearest['remaining_days']} days "
            f"left and it's at {nearest['progress_pct']}% funded."
        )
    while len(plan) < 4:
        plan.append("Review discretionary categories (Entertainment, Shopping) for one-time cuts.")
    return plan[:4]


class AdvisorProvider(ABC):
    @abstractmethod
    def health_audit(self, user_id: int) -> dict:
        ...

    @abstractmethod
    def chat(self, user_id: int, message: str, history: list) -> dict:
        ...


class HeuristicAdvisor(AdvisorProvider):
    """Pure-formula advisor. No network calls. Always available."""

    def health_audit(self, user_id: int) -> dict:
        context = build_financial_context(user_id)
        health = compute_health_score(context)
        roadmap = emergency_liquidity_roadmap(context)
        anomalies = detect_anomalies(context)
        action_plan = build_action_plan(context, roadmap)
        return {
            "source": "heuristic",
            "score": health["score"],
            "grade": health["grade"],
            "components": health["components"],
            "anomalies": anomalies,
            "emergency_roadmap": roadmap,
            "action_plan": action_plan,
            "context": context,
        }

    def chat(self, user_id: int, message: str, history: list) -> dict:
        context = build_financial_context(user_id)
        totals = context["totals"]
        msg_lower = message.lower()
        reply_parts = []

        if "overspend" in msg_lower or "dining" in msg_lower or "over budget" in msg_lower:
            if context["breached_categories"]:
                names = ", ".join(e["category"] for e in context["breached_categories"])
                reply_parts.append(f"You're currently over budget in: {names}.")
            else:
                reply_parts.append("You're not over budget in any category right now — nice work.")
        elif "goal" in msg_lower:
            active = [g for g in context["goals"] if not g["completed"]]
            if active:
                lines = "; ".join(f"{g['name']} ({g['progress_pct']}% funded, {g['remaining_days']}d left)" for g in active)
                reply_parts.append(f"Your active goals: {lines}.")
            else:
                reply_parts.append("You don't have any active savings goals yet — want to set one up?")
        elif "save" in msg_lower or "saving" in msg_lower:
            reply_parts.append(
                f"Your savings rate this month is {totals['savings_rate']}% "
                f"(inflow {totals['total_inflow']}, outflow {totals['total_outflow']})."
            )
        else:
            reply_parts.append(
                f"This month: inflow {totals['total_inflow']}, outflow {totals['total_outflow']}, "
                f"net cash flow {totals['net_cash_flow']}, savings rate {totals['savings_rate']}%."
            )
            if context["breached_categories"]:
                reply_parts.append(
                    f"Heads up — {len(context['breached_categories'])} categor"
                    f"{'y is' if len(context['breached_categories']) == 1 else 'ies are'} over budget."
                )

        return {"source": "heuristic", "reply": " ".join(reply_parts)}


class LLMAdvisor(AdvisorProvider):
    """Gemini-backed advisor. Falls back to HeuristicAdvisor transparently on any failure."""

    def __init__(self):
        self.fallback = HeuristicAdvisor()

    def _call_gemini(self, prompt: str) -> str:
        import requests

        api_key = current_app.config.get("GEMINI_API_KEY")
        model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def health_audit(self, user_id: int) -> dict:
        context = build_financial_context(user_id)
        health = compute_health_score(context)
        roadmap = emergency_liquidity_roadmap(context)
        anomalies = detect_anomalies(context)

        prompt = (
            "You are a personal finance advisor. Using ONLY the JSON financial data below "
            "(do not invent numbers), write a 4-step tactical action plan for next month as a "
            "JSON array of 4 short strings. Data:\n" + json.dumps(context, default=str)
        )
        try:
            raw = self._call_gemini(prompt)
            cleaned = raw.strip().strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            action_plan = json.loads(cleaned)
            if not isinstance(action_plan, list) or not action_plan:
                raise ValueError("bad shape")
            source = "llm"
        except Exception as exc:  # noqa: BLE001 - any failure triggers graceful fallback
            logger.warning("LLM health_audit failed, falling back to heuristic: %s", exc)
            action_plan = build_action_plan(context, roadmap)
            source = "heuristic"

        return {
            "source": source,
            "score": health["score"],
            "grade": health["grade"],
            "components": health["components"],
            "anomalies": anomalies,
            "emergency_roadmap": roadmap,
            "action_plan": action_plan[:4] if isinstance(action_plan, list) else build_action_plan(context, roadmap),
            "context": context,
        }

    def chat(self, user_id: int, message: str, history: list) -> dict:
        context = build_financial_context(user_id)
        history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
        prompt = (
            "You are a helpful, concise personal finance advisor chatbot. "
            "Ground every claim in the JSON financial data below — never invent numbers. "
            f"Conversation so far:\n{history_text}\n\n"
            f"Financial context (JSON):\n{json.dumps(context, default=str)}\n\n"
            f"User: {message}\nAssistant:"
        )
        try:
            reply = self._call_gemini(prompt)
            return {"source": "llm", "reply": reply.strip()}
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM chat failed, falling back to heuristic: %s", exc)
            result = self.fallback.chat(user_id, message, history)
            result["source"] = "heuristic"
            return result


def get_advisor() -> AdvisorProvider:
    api_key = current_app.config.get("GEMINI_API_KEY")
    if api_key:
        return LLMAdvisor()
    logger.info("No GEMINI_API_KEY configured — using HeuristicAdvisor.")
    return HeuristicAdvisor()
