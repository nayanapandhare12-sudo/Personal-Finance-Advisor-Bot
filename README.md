# Ledger — Personal Finance Advisor Bot

A full-stack personal finance manager with an integrated AI advisor that
degrades gracefully to a deterministic heuristic engine whenever an LLM
isn't available.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # fill in SECRET_KEY / GEMINI_API_KEY (optional)
python run.py
```

Open http://localhost:5000. A demo account ("Alex Mercer") with realistic
sample data is created automatically on first run — no signup required.

Run the test suite:

```bash
pytest
```

### Environment variables (`.env`)

| Key | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key |
| `DATABASE_URL` | SQLAlchemy connection string (defaults to local SQLite; point at Postgres in production) |
| `GEMINI_API_KEY` | Optional. If unset, the app runs entirely on `HeuristicAdvisor` |
| `GEMINI_MODEL` | Gemini model identifier (defaults to `gemini-2.0-flash`; use whatever is current at build time) |

## Architecture

```
app/
  routes/      Flask Blueprints — HTTP layer only, no business logic
  services/    Business logic: finance_service.py, advisor.py, budget_rules.py, seed.py
  models/      SQLAlchemy models: User, Income, Expense, Budget, CategoryEnvelope,
               SavingsGoal, ChatMessage
  templates/   Jinja2 + TailwindCSS pages (dashboard, statement, viva)
  static/js/   Vanilla JS — fetch()-based AJAX, Chart.js rendering, no reloads
tests/         pytest coverage for calculations and the heuristic advisor
```

Routes call into `services/`, which call into `models/`. No SQL or financial
math lives in a route handler.

## AI Advisor: LLM ↔ Heuristic Fallback

`AdvisorProvider` is an abstract interface with two implementations:

- **`LLMAdvisor`** — calls the Gemini API, grounded in a JSON snapshot of the
  user's real ledger, envelopes, and goals so the model can't invent numbers.
- **`HeuristicAdvisor`** — computes the identical shape of output (score,
  grade, anomalies, roadmap, action plan) using pure formulas, no network call.

`get_advisor()` returns `LLMAdvisor` only when `GEMINI_API_KEY` is set. Every
Gemini call inside `LLMAdvisor` is wrapped in a `try/except` that falls back
to `HeuristicAdvisor` on **any** failure — missing key, timeout, rate limit,
malformed response — and the route layer wraps the call again as a
last-resort safety net. The UI always shows a badge indicating which engine
answered ("AI-generated" vs. "Offline / heuristic mode"), so the app never
crashes or silently lies about where a number came from.

## Formulas

All thresholds and weights below live in `app/services/budget_rules.py` as a
single source of truth shared by the dashboard, the envelope engine, and the
AI audit.

**Savings Rate %**
```
(Total Inflow − Total Outflow) / Total Inflow × 100
```
Clamped to 0% when inflow is 0, for a given calendar month.

**Budget / Envelope Utilization**
```
Amount Spent / Limit × 100
```
Classified as:
- 🟢 Healthy: < 70%
- 🔵 Moderate: 70–89%
- 🟡 High: 90–99%
- 🔴 Critical (Breached): ≥ 100%

**Financial Health Score (0–100)**

A weighted sum of three sub-scores:

| Component | Weight | What it measures |
|---|---|---|
| Savings rate score | 40% | This month's savings rate, clamped to [0, 100] |
| Envelope adherence score | 35% | Average per-category score: `100 − utilization×0.3` when under budget, `max(0, 70 − overage)` when breached |
| Capital reserves score | 25% | Months of expenses covered by current net cash flow, scaled against a 6-month target |

Letter grade: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, else F.

**Emergency Liquidity Roadmap**

Target reserve = average monthly outflow × 6 months. The gap between target
and current reserve is spread evenly over 12 months to produce a suggested
monthly allocation.

## API Reference (selected)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/dashboard/summary` | Totals, burn rate, category breakdown, envelopes, recent transactions |
| GET/POST | `/api/income`, `/api/expense` | List (with `search`/`category`/`start`/`end` filters) or create a ledger entry |
| DELETE | `/api/income/<id>`, `/api/expense/<id>` | Remove an entry |
| GET/PUT | `/api/budget/cap` | Read/update the monthly spending cap |
| GET/PUT | `/api/budget/envelopes` | Read envelope status / set a category limit |
| GET/POST | `/api/goals` | List / create savings goals |
| POST | `/api/goals/<id>/deposit` | Quick deposit toward a goal |
| GET | `/api/advisor/health-audit` | Run the health audit (LLM or heuristic) |
| POST | `/api/advisor/chat` | Send a chat message to the advisor |
| GET | `/api/account/export` | Full JSON backup |
| POST | `/api/account/reset-demo` | Reset to the sample "Alex Mercer" dataset |
| GET | `/statements?year=&month=` | Printable monthly statement (browser print → PDF) |
| GET | `/viva` | Architecture diagrams + 10 Viva Q&A pairs |

## Notes

- This build targets the Gemini API but keeps the provider swappable —
  `LLMAdvisor._call_gemini` is the only place that speaks to a specific
  vendor's API shape, so swapping providers means replacing that one method.
- SQLite is used for local/demo use; `DATABASE_URL` can point at Postgres
  in production without any model changes since access goes through the
  SQLAlchemy ORM.
