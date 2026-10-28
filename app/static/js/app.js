(function () {
  let categoryChart = null;
  let currentDepositGoalId = null;

  const $ = (id) => document.getElementById(id);

  function statusClass(status) {
    return `status-${status}`;
  }

  async function refreshAll() {
    await Promise.all([refreshDashboard(), refreshIncomeList(), refreshExpenseList(), refreshGoals(), refreshAudit()]);
  }

  // ---------- Dashboard summary ----------
  async function refreshDashboard() {
    const res = await fetch("/api/dashboard/summary");
    const data = await res.json();

    $("userName").textContent = data.user.name.split(" ")[0];

    $("totalInflow").textContent = formatMoney(data.totals.total_inflow);
    $("totalOutflow").textContent = formatMoney(data.totals.total_outflow);
    $("netCashFlow").textContent = formatMoney(data.totals.net_cash_flow);
    $("savingsRate").textContent = `${data.totals.savings_rate}%`;

    const burn = data.burn;
    $("burnBar").style.width = `${Math.min(burn.utilization_pct, 100)}%`;
    $("burnBar").style.background = {
      healthy: "#1f5c47", moderate: "#1d4e89", high: "#a8631a", critical: "#a3312a",
    }[burn.status];
    $("burnBadge").textContent = `${burn.status_label} · ${burn.utilization_pct}%`;
    $("burnBadge").className = `text-xs px-2 py-1 rounded-full font-medium ${statusClass(burn.status)}`;
    $("burnSpent").textContent = formatMoney(burn.spent);
    $("burnCap").textContent = formatMoney(burn.cap);

    renderEnvelopes(data.envelopes);
    renderCategoryChart(data.category_breakdown);
    renderRecentTransactions(data.recent_transactions);
  }

  function renderEnvelopes(envelopes) {
    $("envelopeList").innerHTML = envelopes
      .filter((e) => e.limit > 0 || e.spent > 0)
      .map(
        (e) => `
      <div class="flex items-center gap-2">
        <span class="w-32 shrink-0 truncate">${e.category}</span>
        <div class="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
          <div class="h-full rounded-full" style="width:${Math.min(e.utilization_pct, 100)}%; background:${{healthy:"#1f5c47",moderate:"#1d4e89",high:"#a8631a",critical:"#a3312a"}[e.status]}"></div>
        </div>
        <span class="text-xs w-24 text-right figure">${formatMoney(e.spent)} / ${formatMoney(e.limit)}</span>
        <span class="text-xs px-2 py-0.5 rounded-full ${statusClass(e.status)}">${e.status_label}</span>
      </div>`
      )
      .join("");
  }

  function renderCategoryChart(breakdown) {
    const nonZero = breakdown.filter((b) => b.amount > 0);
    const labels = nonZero.map((b) => b.category);
    const values = nonZero.map((b) => b.amount);
    const ctx = document.getElementById("categoryChart");
    if (categoryChart) categoryChart.destroy();
    categoryChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ["#1f5c47","#1d4e89","#a8631a","#a3312a","#6b4e9c","#2f7a68","#7a5c2f","#4a6a8a","#8a4a5c","#5c7a3f"],
        }],
      },
      options: { plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } } } },
    });
  }

  function renderRecentTransactions(items) {
    $("recentTransactions").innerHTML = items
      .map(
        (t) => `
      <div class="flex items-center justify-between py-2">
        <div>
          <p>${t.category} <span class="text-[var(--ink)]/50">· ${t.description || "—"}</span></p>
          <p class="text-xs text-[var(--ink)]/50">${t.date}</p>
        </div>
        <p class="figure ${t.type === "income" ? "text-[var(--forest)]" : "text-[var(--red)]"}">
          ${t.type === "income" ? "+" : "-"}${formatMoney(t.amount)}
        </p>
      </div>`
      )
      .join("");
  }

  // ---------- Income / Expense ledgers ----------
  async function refreshIncomeList() {
    const params = new URLSearchParams();
    const search = $("incomeSearch").value;
    const cat = $("incomeFilterCategory").value;
    if (search) params.set("search", search);
    if (cat) params.set("category", cat);
    const res = await fetch(`/api/income?${params}`);
    const items = await res.json();
    $("incomeList").innerHTML = items
      .map(
        (i) => `
      <div class="flex items-center justify-between py-2">
        <div><p>${i.category} <span class="text-[var(--ink)]/50">· ${i.description || "—"}</span></p><p class="text-xs text-[var(--ink)]/50">${i.date}</p></div>
        <div class="flex items-center gap-2">
          <span class="figure text-[var(--forest)]">+${formatMoney(i.amount)}</span>
          <button data-id="${i.id}" class="deleteIncome text-xs text-[var(--red)] underline">delete</button>
        </div>
      </div>`
      )
      .join("") || `<p class="text-xs text-[var(--ink)]/50 py-2">No income entries yet.</p>`;

    document.querySelectorAll(".deleteIncome").forEach((btn) =>
      btn.addEventListener("click", async () => {
        await fetch(`/api/income/${btn.dataset.id}`, { method: "DELETE" });
        await refreshAll();
      })
    );
  }

  async function refreshExpenseList() {
    const params = new URLSearchParams();
    const search = $("expenseSearch").value;
    const cat = $("expenseFilterCategory").value;
    if (search) params.set("search", search);
    if (cat) params.set("category", cat);
    const res = await fetch(`/api/expense?${params}`);
    const items = await res.json();
    $("expenseList").innerHTML = items
      .map(
        (e) => `
      <div class="flex items-center justify-between py-2">
        <div><p>${e.category} <span class="text-[var(--ink)]/50">· ${e.description || "—"}</span></p><p class="text-xs text-[var(--ink)]/50">${e.date}</p></div>
        <div class="flex items-center gap-2">
          <span class="figure text-[var(--red)]">-${formatMoney(e.amount)}</span>
          <button data-id="${e.id}" class="deleteExpense text-xs text-[var(--red)] underline">delete</button>
        </div>
      </div>`
      )
      .join("") || `<p class="text-xs text-[var(--ink)]/50 py-2">No expense entries yet.</p>`;

    document.querySelectorAll(".deleteExpense").forEach((btn) =>
      btn.addEventListener("click", async () => {
        await fetch(`/api/expense/${btn.dataset.id}`, { method: "DELETE" });
        await refreshAll();
      })
    );
  }

  $("incomeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = Object.fromEntries(fd.entries());
    payload.amount = window.toBaseCurrency ? window.toBaseCurrency(payload.amount) : payload.amount;
    const res = await fetch("/api/income", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    if (res.ok) { e.target.reset(); await refreshAll(); }
    else { const err = await res.json(); alert(err.errors.join("\n")); }
  });

  $("expenseForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = Object.fromEntries(fd.entries());
    payload.amount = window.toBaseCurrency ? window.toBaseCurrency(payload.amount) : payload.amount;
    const res = await fetch("/api/expense", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    if (res.ok) { e.target.reset(); await refreshAll(); }
    else { const err = await res.json(); alert(err.errors.join("\n")); }
  });

  $("incomeSearch").addEventListener("input", debounce(refreshIncomeList, 250));
  $("incomeFilterCategory").addEventListener("change", refreshIncomeList);
  $("expenseSearch").addEventListener("input", debounce(refreshExpenseList, 250));
  $("expenseFilterCategory").addEventListener("change", refreshExpenseList);

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  // ---------- Budget cap ----------
  $("editCapBtn").addEventListener("click", async () => {
    const current = await (await fetch("/api/budget/cap")).json();
    const symbol = window.getCurrencySymbol ? window.getCurrencySymbol() : "₹";
    const displayCurrent = window.fromBaseCurrency ? window.fromBaseCurrency(current.monthly_spending_cap) : current.monthly_spending_cap;
    const val = prompt(`Set monthly spending cap (${symbol})`, Math.round(displayCurrent * 100) / 100);
    if (val === null) return;
    const baseVal = window.toBaseCurrency ? window.toBaseCurrency(val) : parseFloat(val);
    const res = await fetch("/api/budget/cap", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monthly_spending_cap: baseVal }),
    });
    if (res.ok) await refreshDashboard();
    else alert("Please enter a valid positive number.");
  });

  // ---------- Savings goals ----------
  async function refreshGoals() {
    const res = await fetch("/api/goals");
    const goals = await res.json();
    $("goalsList").innerHTML = goals
      .map(
        (g) => `
      <div class="border border-[var(--line)] rounded-lg p-4">
        <div class="flex items-center justify-between">
          <p class="font-semibold text-sm">${g.name}</p>
          ${g.completed ? '<span class="text-xs px-2 py-0.5 rounded-full status-healthy">Complete</span>' : ""}
        </div>
        <p class="text-xs text-[var(--ink)]/50 mt-1">${g.remaining_days} days left</p>
        <div class="w-full h-2 bg-black/5 rounded-full overflow-hidden mt-2">
          <div class="h-full bg-[var(--forest)] rounded-full" style="width:${g.progress_pct}%"></div>
        </div>
        <p class="text-xs mt-1 figure">${formatMoney(g.current_amount)} of ${formatMoney(g.target_amount)} (${g.progress_pct}%)</p>
        <div class="flex gap-2 mt-3">
          ${!g.completed ? `<button data-id="${g.id}" data-name="${g.name}" class="depositBtn text-xs px-2 py-1 rounded border border-[var(--line)]">Deposit</button>` : ""}
          <button data-id="${g.id}" class="deleteGoal text-xs px-2 py-1 rounded border border-[var(--line)] text-[var(--red)]">Delete</button>
        </div>
      </div>`
      )
      .join("") || `<p class="text-xs text-[var(--ink)]/50">No goals yet — create one to get started.</p>`;

    document.querySelectorAll(".depositBtn").forEach((btn) =>
      btn.addEventListener("click", () => {
        currentDepositGoalId = btn.dataset.id;
        $("depositGoalName").textContent = btn.dataset.name;
        $("depositDialog").showModal();
      })
    );
    document.querySelectorAll(".deleteGoal").forEach((btn) =>
      btn.addEventListener("click", async () => {
        await fetch(`/api/goals/${btn.dataset.id}`, { method: "DELETE" });
        await refreshGoals();
      })
    );
  }

  $("newGoalBtn").addEventListener("click", () => $("goalDialog").showModal());
  $("closeGoalDialog").addEventListener("click", () => $("goalDialog").close());
  $("goalForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = Object.fromEntries(fd.entries());
    payload.target_amount = window.toBaseCurrency ? window.toBaseCurrency(payload.target_amount) : payload.target_amount;
    if (payload.current_amount) {
      payload.current_amount = window.toBaseCurrency ? window.toBaseCurrency(payload.current_amount) : payload.current_amount;
    }
    const res = await fetch("/api/goals", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    if (res.ok) { e.target.reset(); $("goalDialog").close(); await refreshGoals(); }
    else { const err = await res.json(); alert(err.errors.join("\n")); }
  });

  $("closeDepositDialog").addEventListener("click", () => $("depositDialog").close());
  document.querySelectorAll(".depositChip").forEach((chip) =>
    chip.addEventListener("click", async () => {
      const displayAmount = parseFloat(chip.dataset.amount);
      const baseAmount = window.toBaseCurrency ? window.toBaseCurrency(displayAmount) : displayAmount;
      await submitDeposit(baseAmount);
    })
  );
  $("depositForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const amt = parseFloat($("depositAmount").value);
    if (!amt || amt <= 0) return;
    const baseAmount = window.toBaseCurrency ? window.toBaseCurrency(amt) : amt;
    await submitDeposit(baseAmount);
  });
  async function submitDeposit(amount) {
    await fetch(`/api/goals/${currentDepositGoalId}/deposit`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount }),
    });
    $("depositAmount").value = "";
    $("depositDialog").close();
    await refreshGoals();
  }

  // ---------- AI advisor: health audit ----------
  async function refreshAudit() {
    const res = await fetch("/api/advisor/health-audit");
    const data = await res.json();

    $("advisorSourceBadge").textContent = data.source === "llm" ? "AI-generated" : "Offline / heuristic mode";
    $("advisorSourceBadge").className = `text-xs px-2 py-1 rounded-full ${data.source === "llm" ? "status-healthy" : "status-moderate"}`;

    const circumference = 326.7;
    const offset = circumference - (data.score / 100) * circumference;
    $("scoreRing").style.strokeDashoffset = offset;
    $("scoreText").textContent = data.score;
    $("gradeText").textContent = data.grade;

    $("anomalyList").innerHTML = data.anomalies.length
      ? data.anomalies.map((a) => `<li>${a}</li>`).join("")
      : `<li class="text-[var(--forest)] list-none">No anomalies detected — spending looks healthy.</li>`;

    const rm = data.emergency_roadmap;
    $("roadmapText").textContent =
      `You have ${formatMoney(rm.current_reserve)} (${rm.months_covered} months) toward a ${rm.target_months}-month reserve of ${formatMoney(rm.target_reserve)}. ` +
      (rm.gap > 0 ? `Save ${formatMoney(rm.suggested_monthly_allocation)}/month to close the gap in a year.` : `Target already met.`);

    $("actionPlanList").innerHTML = data.action_plan.map((step) => `<li>${step}</li>`).join("");
  }
  $("refreshAuditBtn").addEventListener("click", refreshAudit);

  // ---------- AI advisor: chat ----------
  async function loadChatHistory() {
    const res = await fetch("/api/advisor/chat/history");
    const msgs = await res.json();
    renderChat(msgs);
  }

  function renderChat(msgs) {
    $("chatMessages").innerHTML = msgs
      .map(
        (m) => `
      <div class="flex ${m.role === "user" ? "justify-end" : "justify-start"}">
        <div class="max-w-[80%] rounded-lg px-3 py-2 ${m.role === "user" ? "bg-[var(--forest)] text-white" : "bg-black/5"}">
          ${m.content}
        </div>
      </div>`
      )
      .join("");
    $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
    if (msgs.length) {
      const last = msgs[msgs.length - 1];
      if (last.role === "assistant") {
        $("chatSourceBadge").textContent = last.source === "llm" ? "AI-generated" : "Offline / heuristic mode";
        $("chatSourceBadge").className = `text-xs px-2 py-1 rounded-full ${last.source === "llm" ? "status-healthy" : "status-moderate"}`;
      }
    }
  }

  async function loadChatSuggestions() {
    const res = await fetch("/api/advisor/chat/suggestions");
    const suggestions = await res.json();
    $("chatSuggestions").innerHTML = suggestions
      .map((s) => `<button type="button" class="suggestionChip px-2 py-1 rounded-full border border-[var(--line)]">${s}</button>`)
      .join("");
    document.querySelectorAll(".suggestionChip").forEach((chip) =>
      chip.addEventListener("click", () => {
        $("chatInput").value = chip.textContent;
        $("chatForm").dispatchEvent(new Event("submit", { cancelable: true }));
      })
    );
  }

  $("chatForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = $("chatInput").value.trim();
    if (!message) return;
    $("chatInput").value = "";
    const res = await fetch("/api/advisor/chat", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }),
    });
    if (res.ok) await loadChatHistory();
  });

  // ---------- Reset demo / export ----------
  $("resetDemoBtn").addEventListener("click", async () => {
    if (!confirm("This will replace all data with the sample dataset. Continue?")) return;
    await fetch("/api/account/reset-demo", { method: "POST" });
    await refreshAll();
    await loadChatHistory();
  });

  $("exportBtn").addEventListener("click", async () => {
    const res = await fetch("/api/account/export");
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `finance-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  function updateAmountPlaceholders() {
    const symbol = window.getCurrencySymbol ? window.getCurrencySymbol() : "₹";
    if ($("incomeAmountInput")) $("incomeAmountInput").placeholder = `Amount (${symbol})`;
    if ($("expenseAmountInput")) $("expenseAmountInput").placeholder = `Amount (${symbol})`;
    if ($("depositAmount")) $("depositAmount").placeholder = `Custom amount (${symbol})`;
    if ($("goalTargetInput")) $("goalTargetInput").placeholder = `Target amount (${symbol})`;
    if ($("goalCurrentInput")) $("goalCurrentInput").placeholder = `Starting amount (${symbol}, optional)`;
    document.querySelectorAll(".chipSymbol").forEach((el) => { el.textContent = symbol; });
  }

  document.addEventListener("currencychange", () => { refreshAll(); updateAmountPlaceholders(); });

  document.addEventListener("DOMContentLoaded", async () => {
    updateAmountPlaceholders();
    await refreshAll();
    await loadChatHistory();
    await loadChatSuggestions();
  });
})();
