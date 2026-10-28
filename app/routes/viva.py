from flask import Blueprint, render_template, jsonify

viva_bp = Blueprint("viva", __name__)

VIVA_QA = [
    {
        "q": "What architectural pattern does this application follow?",
        "a": "A layered architecture: Flask Blueprints (routes) handle HTTP concerns only, "
             "services/ hold business logic (finance calculations, the AI advisor), and "
             "models/ define SQLAlchemy ORM entities. No business logic lives inside route handlers.",
    },
    {
        "q": "How is the Savings Rate calculated?",
        "a": "Savings Rate % = (Total Inflow - Total Outflow) / Total Inflow * 100, computed per "
             "calendar month and clamped to 0 when there is no inflow, to avoid division errors.",
    },
    {
        "q": "How is the Financial Health Score computed?",
        "a": "A weighted sum of three normalized 0-100 sub-scores: savings rate (40%), envelope "
             "adherence (35%) — how well spending stays inside category limits — and capital "
             "reserves (25%) — months of expenses covered by current net cash flow versus a "
             "6-month target. Weights live in one place (budget_rules.py) for consistency.",
    },
    {
        "q": "How is Budget Burn Rate / utilization status determined?",
        "a": "Utilization % = amount spent / envelope or cap limit * 100. It is classified as "
             "Healthy (<70%), Moderate (70-89%), High (90-99%), or Critical/Breached (>=100%), "
             "using centrally defined thresholds in budget_rules.py shared by the dashboard, "
             "envelope engine, and AI audit.",
    },
    {
        "q": "What happens if the Gemini API key is missing or the request fails?",
        "a": "The AdvisorProvider interface has two implementations: LLMAdvisor and "
             "HeuristicAdvisor. get_advisor() picks LLMAdvisor only when a key is configured, "
             "and every LLM call inside it is wrapped in a try/except that falls back to the "
             "same-shaped heuristic output on any error (missing key, timeout, rate limit, bad "
             "JSON). The route layer wraps advisor calls again as a last-resort safety net, so "
             "the UI never crashes and always shows which source produced the answer.",
    },
    {
        "q": "What security measures does the app take?",
        "a": "Server-side input validation on every form/endpoint (amount, category enum, date "
             "format) before any database write; parameterized queries via the SQLAlchemy ORM to "
             "prevent SQL injection; secrets (API keys, SECRET_KEY) loaded from environment "
             "variables via .env and never hard-coded; and the AI prompt is explicitly grounded "
             "in server-computed JSON so the model cannot fabricate or leak unrelated data.",
    },
    {
        "q": "How does the Emergency Liquidity Roadmap work?",
        "a": "It targets 6 months of average monthly outflow as a reserve. Current reserve is "
             "approximated from net cash flow; the gap to the target is spread evenly over 12 "
             "months to produce a suggested monthly allocation, so the advice is always "
             "achievable rather than a lump sum demand.",
    },
    {
        "q": "Why is a heuristic fallback considered good design here, not just a workaround?",
        "a": "It guarantees the core value proposition (an always-available financial health "
             "assessment) is never dependent on a third-party network call, keeps the app "
             "demo-safe offline, and — because both engines share the same formulas in "
             "finance_service.py and budget_rules.py — the two produce consistent, testable "
             "numbers rather than diverging behavior.",
    },
    {
        "q": "How does the dashboard update without full page reloads?",
        "a": "All mutating actions (add/delete income or expense, deposit to a goal, change an "
             "envelope limit) are fired via fetch() to JSON REST endpoints; the client then "
             "re-fetches /api/dashboard/summary and re-renders the totals, charts, and badges "
             "in place using vanilla JS DOM updates and Chart.js's update() method.",
    },
    {
        "q": "How is multi-currency support implemented without re-querying the database?",
        "a": "All amounts are stored and calculated in a single base unit (USD-equivalent). "
             "The currency switcher applies a client-side conversion rate lookup "
             "(app/services/budget_rules.py CURRENCIES) to the already-fetched totals, so "
             "switching currency is an instant re-render, not a new database roundtrip.",
    },
]


@viva_bp.route("/viva")
def viva_page():
    return render_template("viva.html", qa_pairs=VIVA_QA)


@viva_bp.route("/api/viva")
def viva_api():
    return jsonify(VIVA_QA)
