// Handles the currency selector in the nav bar.
//
// All amounts are stored internally in a single BASE_CURRENCY (INR) so the
// ledger's totals always stay mathematically consistent. The toggle applies
// real exchange-rate math (via budget_rules.CURRENCIES' rate_per_usd figures)
// in both directions:
//   - Display: fromBaseCurrency() converts stored INR amounts into whichever
//     currency is selected, for every total, ledger row, envelope bar, goal,
//     and statement.
//   - Entry: toBaseCurrency() converts what you type into Add Income /
//     Add Expense / deposits / the spending cap back into INR before it's
//     sent to the server, so the ledger never mixes currencies internally.
(function () {
  const BASE_CURRENCY = "INR";
  let currentCurrency = "INR";

  function rateInfo(code) {
    const rates = window.APP_CURRENCIES || {};
    return rates[code] || rates[BASE_CURRENCY] || { symbol: "\u20b9", rate_per_usd: 83 };
  }

  // Stored (INR) amount -> amount in whichever currency is passed (defaults
  // to the currently selected one). Both rates are expressed per 1 USD, so
  // going through a USD-equivalent midpoint lets us convert between any pair.
  window.fromBaseCurrency = function (baseAmount, code) {
    code = code || window.CURRENT_CURRENCY || currentCurrency;
    const base = rateInfo(BASE_CURRENCY);
    const target = rateInfo(code);
    const usdEquivalent = (baseAmount || 0) / base.rate_per_usd;
    return usdEquivalent * target.rate_per_usd;
  };

  // Amount typed in the currently selected currency -> INR for storage.
  window.toBaseCurrency = function (displayAmount, code) {
    code = code || window.CURRENT_CURRENCY || currentCurrency;
    const base = rateInfo(BASE_CURRENCY);
    const target = rateInfo(code);
    const usdEquivalent = (parseFloat(displayAmount) || 0) / target.rate_per_usd;
    return usdEquivalent * base.rate_per_usd;
  };

  async function loadCurrencies() {
    const res = await fetch("/api/account/currencies");
    const rates = await res.json();
    window.APP_CURRENCIES = rates;
    window.CURRENT_CURRENCY = currentCurrency;
    const sel = document.getElementById("currencySelect");
    if (!sel) return;
    sel.innerHTML = Object.entries(rates)
      .map(([code, info]) => `<option value="${code}">${info.flag} ${code}</option>`)
      .join("");
    sel.value = currentCurrency;
    sel.addEventListener("change", async (e) => {
      currentCurrency = e.target.value;
      window.CURRENT_CURRENCY = currentCurrency;
      await fetch("/api/account/currency", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currency: currentCurrency }),
      });
      document.dispatchEvent(new CustomEvent("currencychange", { detail: currentCurrency }));
    });
  }

  window.formatMoney = function (baseAmount) {
    const code = window.CURRENT_CURRENCY || currentCurrency;
    const target = rateInfo(code);
    const converted = window.fromBaseCurrency(baseAmount, code);
    const decimals = code === "JPY" || code === "KRW" ? 0 : 2;
    return `${target.symbol}${converted.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
  };

  window.getCurrencySymbol = function () {
    const code = window.CURRENT_CURRENCY || currentCurrency;
    return rateInfo(code).symbol;
  };

  document.addEventListener("DOMContentLoaded", loadCurrencies);
})();
