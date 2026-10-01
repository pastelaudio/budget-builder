// Set this to your deployed Flask backend's URL when hosting this page separately
// (e.g. on Netlify). Leave empty ("") when Flask itself serves this page.
const API_BASE_URL = "";

const CURRENCIES = {
  USD: "$", EUR: "€", GBP: "£", CAD: "$", AUD: "$",
  JPY: "¥", INR: "₹", CHF: "CHF", MXN: "$", BRL: "R$", PHP: "₱",
};
const DEFAULT_CURRENCY = "USD";

const DEFAULT_INCOME = [
  ["Primary Income", 0],
  ["Other Income", 0],
];

const DEFAULT_EXPENSES = [
  ["Rent / Mortgage", 0, 0],
  ["Utilities", 0, 0],
  ["Groceries", 0, 0],
  ["Transportation", 0, 0],
  ["Insurance", 0, 0],
  ["Debt Payments", 0, 0],
  ["Subscriptions", 0, 0],
  ["Entertainment", 0, 0],
  ["Savings", 0, 0],
  ["Miscellaneous", 0, 0],
];

const PIE_COLORS = [
  "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
  "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
];

const SESSION_KEY = "budgetBuilderSessions";
let autosaveTimer = null;

function loadAllSessions() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY)) || {};
  } catch {
    return {};
  }
}

function listSavedMonths() {
  const data = loadAllSessions();
  return Object.keys(data).sort((a, b) => (data[b].savedAt || "").localeCompare(data[a].savedAt || ""));
}

function saveSession(month, currency, incomes, expenses) {
  if (!month) return;
  const data = loadAllSessions();
  data[month] = { currency, incomes, expenses, savedAt: new Date().toISOString() };
  localStorage.setItem(SESSION_KEY, JSON.stringify(data));
  refreshSavedMonthsSelect(month);
}

function loadSession(month) {
  return loadAllSessions()[month] || null;
}

function deleteSession(month) {
  const data = loadAllSessions();
  delete data[month];
  localStorage.setItem(SESSION_KEY, JSON.stringify(data));
}

function refreshSavedMonthsSelect(selectMonth) {
  const select = $("saved-months");
  const months = listSavedMonths();
  select.innerHTML = months.length
    ? months.map((m) => `<option value="${m}">${m}</option>`).join("")
    : `<option value="">— none saved —</option>`;
  if (selectMonth && months.includes(selectMonth)) select.value = selectMonth;
}

function scheduleAutosave() {
  if (autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    const payload = buildPayload();
    saveSession(payload.month, payload.currency, payload.incomes, payload.expenses);
  }, 800);
}

function applySessionToForm(data) {
  $("income-rows").innerHTML = "";
  $("expense-rows").innerHTML = "";
  (data.incomes || []).forEach((r) => addRow($("income-rows"), "income", [r.name, r.amount]));
  (data.expenses || []).forEach((r) => addRow($("expense-rows"), "expense", [r.name, r.budgeted, r.actual]));
  if (data.currency) $("currency").value = data.currency;
  refreshAll();
}

const $ = (id) => document.getElementById(id);
const toFloat = (v) => {
  const n = parseFloat(String(v).replace(/,/g, "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
};

function addRow(container, kind, values) {
  const row = document.createElement("div");
  row.className = "row";
  if (kind === "income") {
    row.innerHTML = `
      <input type="text" class="name" placeholder="Source" value="${values?.[0] ?? ""}">
      <input type="number" class="amount" step="0.01" value="${values?.[1] ?? ""}">
      <button class="btn remove" title="Remove">✕</button>`;
  } else {
    row.innerHTML = `
      <input type="text" class="name" placeholder="Category" value="${values?.[0] ?? ""}">
      <input type="number" class="budgeted" step="0.01" value="${values?.[1] ?? ""}">
      <input type="number" class="actual" step="0.01" value="${values?.[2] ?? ""}">
      <span class="diff">0.00</span>
      <button class="btn remove" title="Remove">✕</button>`;
  }
  row.querySelector(".remove").addEventListener("click", () => {
    row.remove();
    refreshAll();
    scheduleAutosave();
  });
  row.querySelectorAll("input").forEach((el) => el.addEventListener("input", () => {
    refreshAll();
    scheduleAutosave();
  }));
  container.appendChild(row);
}

function getIncomeRows() {
  return [...$("income-rows").children]
    .map((row) => ({
      name: row.querySelector(".name").value.trim(),
      amount: toFloat(row.querySelector(".amount").value),
    }))
    .filter((r) => r.name);
}

function getExpenseRows() {
  return [...$("expense-rows").children]
    .map((row) => ({
      name: row.querySelector(".name").value.trim(),
      budgeted: toFloat(row.querySelector(".budgeted").value),
      actual: toFloat(row.querySelector(".actual").value),
    }))
    .filter((r) => r.name);
}

function currencySymbol() {
  return CURRENCIES[$("currency").value] || CURRENCIES[DEFAULT_CURRENCY];
}

function refreshSummaryAndDiffs() {
  const symbol = currencySymbol();
  let totalIncome = 0;
  getIncomeRows().forEach((r) => (totalIncome += r.amount));

  let totalExpenses = 0;
  [...$("expense-rows").children].forEach((row) => {
    const budgeted = toFloat(row.querySelector(".budgeted").value);
    const actual = toFloat(row.querySelector(".actual").value);
    const diff = budgeted - actual;
    totalExpenses += actual;
    const diffEl = row.querySelector(".diff");
    diffEl.textContent = `${symbol}${diff.toFixed(2)}`;
    diffEl.classList.toggle("negative", diff < 0);
  });

  const remaining = totalIncome - totalExpenses;
  const rate = totalIncome > 0 ? (remaining / totalIncome) * 100 : 0;

  $("sum-income").textContent = `${symbol}${totalIncome.toFixed(2)}`;
  $("sum-expenses").textContent = `${symbol}${totalExpenses.toFixed(2)}`;
  $("sum-remaining").textContent = `${symbol}${remaining.toFixed(2)}`;
  $("sum-rate").textContent = `${rate.toFixed(1)}%`;
}

function refreshChart() {
  const symbol = currencySymbol();
  const canvas = $("pie-canvas");
  const ctx = canvas.getContext("2d");
  const legend = $("legend");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  legend.innerHTML = "";

  const slices = getExpenseRows()
    .map((r) => ({ name: r.name, amount: r.actual > 0 ? r.actual : r.budgeted }))
    .filter((r) => r.amount > 0);

  const total = slices.reduce((sum, s) => sum + s.amount, 0);
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const radius = Math.min(cx, cy) - 10;

  if (total <= 0) {
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--fg");
    ctx.textAlign = "center";
    ctx.font = "13px sans-serif";
    ctx.fillText("Add expense amounts", cx, cy - 8);
    ctx.fillText("to see the breakdown", cx, cy + 10);
    return;
  }

  let startAngle = -Math.PI / 2;
  slices.forEach((slice, i) => {
    const color = PIE_COLORS[i % PIE_COLORS.length];
    const sliceAngle = (slice.amount / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    startAngle += sliceAngle;

    const pct = (100 * slice.amount) / total;
    const legendRow = document.createElement("div");
    legendRow.className = "legend-row";
    legendRow.innerHTML = `<span class="legend-swatch" style="background:${color}"></span>
      <span>${slice.name}: ${symbol}${slice.amount.toFixed(2)} (${pct.toFixed(1)}%)</span>`;
    legend.appendChild(legendRow);
  });
}

function refreshAll() {
  refreshSummaryAndDiffs();
  refreshChart();
}

function setStatus(text, isError) {
  const el = $("status");
  el.textContent = text;
  el.style.color = isError ? "#e15759" : "";
}

async function exportExcel() {
  const payload = buildPayload();
  saveSession(payload.month, payload.currency, payload.incomes, payload.expenses);
  setStatus("Generating Excel workbook...");
  try {
    const res = await fetch(`${API_BASE_URL}/export/excel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Budget_${payload.month.replace(/\s+/g, "_")}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus("Excel workbook downloaded.");
  } catch (err) {
    setStatus(`Failed to export Excel: ${err.message}`, true);
  }
}

async function exportSheets() {
  const payload = buildPayload();
  saveSession(payload.month, payload.currency, payload.incomes, payload.expenses);
  setStatus("Creating Google Sheet...");
  try {
    const res = await fetch(`${API_BASE_URL}/export/sheets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Unknown error");
    setStatus(`Created: ${data.url}`);
    window.open(data.url, "_blank");
  } catch (err) {
    setStatus(`Failed to create Google Sheet: ${err.message}`, true);
  }
}

function buildPayload() {
  return {
    month: $("month").value.trim() || new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" }),
    currency: $("currency").value,
    incomes: getIncomeRows(),
    expenses: getExpenseRows(),
  };
}

function init() {
  $("month").value = new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" });
  $("month").addEventListener("input", scheduleAutosave);

  const currencySelect = $("currency");
  Object.keys(CURRENCIES).sort().forEach((code) => {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = code;
    if (code === DEFAULT_CURRENCY) opt.selected = true;
    currencySelect.appendChild(opt);
  });
  currencySelect.addEventListener("change", () => {
    refreshAll();
    scheduleAutosave();
  });

  refreshSavedMonthsSelect();
  const savedMonths = listSavedMonths();
  if (savedMonths.length) {
    applySessionToForm(loadSession(savedMonths[0]));
    $("month").value = savedMonths[0];
    refreshSavedMonthsSelect(savedMonths[0]);
  } else {
    DEFAULT_INCOME.forEach((row) => addRow($("income-rows"), "income", row));
    DEFAULT_EXPENSES.forEach((row) => addRow($("expense-rows"), "expense", row));
  }

  document.querySelectorAll(".add-row").forEach((btn) => {
    btn.addEventListener("click", () => {
      addRow($(btn.dataset.target), btn.dataset.kind);
      refreshAll();
      scheduleAutosave();
    });
  });

  $("export-excel").addEventListener("click", exportExcel);
  $("export-sheets").addEventListener("click", exportSheets);
  $("refresh-chart").addEventListener("click", refreshAll);

  $("load-month").addEventListener("click", () => {
    const month = $("saved-months").value;
    if (!month) return;
    const data = loadSession(month);
    if (!data) return;
    $("month").value = month;
    applySessionToForm(data);
    setStatus(`Loaded saved session: ${month}`);
  });

  $("delete-month").addEventListener("click", () => {
    const month = $("saved-months").value;
    if (!month) return;
    if (!confirm(`Delete saved session for '${month}'?`)) return;
    deleteSession(month);
    refreshSavedMonthsSelect();
    setStatus(`Deleted saved session: ${month}`);
  });

  $("theme-toggle").addEventListener("click", () => {
    const isDark = document.body.classList.toggle("theme-light") === false;
    $("theme-toggle").textContent = isDark ? "☀ Light mode" : "🌙 Dark mode";
    refreshChart();
  });

  refreshAll();
}

document.addEventListener("DOMContentLoaded", init);
