const state = {
  transactions: [],
  manualSubscriptions: [],
  report: null,
};

const $ = (id) => document.getElementById(id);
const money = (value) => `$${Number(value || 0).toFixed(2)}`;

async function api(path, payload) {
  const response = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : {},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json();
  if (!response.ok || data.error) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function setMetadata(text) {
  $("metadata").textContent = text;
}

function renderTransactions() {
  const rows = state.transactions.slice(0, 80).map((tx) => `
    <tr>
      <td>${tx.date}</td>
      <td>${escapeHtml(tx.description)}</td>
      <td>${money(tx.amount)}</td>
      <td>${tx.source}</td>
    </tr>
  `).join("");
  $("transactionRows").innerHTML = rows || `<tr><td colspan="4">No transactions imported yet.</td></tr>`;

  $("manualRows").innerHTML = state.manualSubscriptions.map((item) =>
    `<span class="chip">${escapeHtml(item.merchant)} · ${money(item.amount)} · ${item.cadence}</span>`
  ).join("") || `<span class="muted">No manual subscriptions added.</span>`;
}

function renderReport(report) {
  $("metricCount").textContent = report.summary.subscription_count;
  $("metricAnnual").textContent = money(report.summary.annualized_cost);
  $("metricMonthly").textContent = money(report.summary.monthly_equivalent);
  $("metricReview").textContent = report.summary.needs_review_count;

  $("queue").innerHTML = report.action_queue.map((row) => {
    const risk = row.priority_score >= 55 ? "risk-high" : row.priority_score >= 35 ? "risk-medium" : "";
    return `<div class="queue-item ${risk}">
      <strong>${escapeHtml(row.merchant)}</strong>
      <span class="pill">${row.recommended_action}</span>
      <span class="pill">score ${row.priority_score}</span>
      <p>${money(row.annualized_cost)}/yr · renewal ${row.next_renewal_estimate} · confidence ${row.confidence}</p>
      <p>${row.reasons.map(escapeHtml).join(", ") || "No urgent cancellation signal."}</p>
      ${row.cancellation_url ? `<a href="${row.cancellation_url}" target="_blank" rel="noreferrer">Cancellation/help page</a>` : ""}
    </div>`;
  }).join("") || `<p class="muted">No subscriptions detected.</p>`;

  $("timeline").innerHTML = report.renewal_timeline.slice(0, 12).map((row) => `
    <div class="timeline-item">
      <strong>${escapeHtml(row.merchant)}</strong>
      <span class="pill">${row.days_until} days</span>
      <span class="pill">${money(row.amount)}</span>
      <p>${row.next_renewal_estimate} · ${row.review_flags.join(", ") || "no flags"}</p>
    </div>
  `).join("") || `<p class="muted">No renewal estimates yet.</p>`;

  $("categories").innerHTML = Object.entries(report.category_summary).map(([category, row]) => `
    <div class="category-item">
      <strong>${escapeHtml(category)}</strong>
      <p>${row.count} subscription(s) · ${money(row.annualized_cost)}/yr</p>
      <p>${row.merchants.map(escapeHtml).join(", ")}</p>
    </div>
  `).join("") || `<p class="muted">No category summary yet.</p>`;

  $("savings").innerHTML = Object.entries(report.savings_scenarios).map(([key, value]) => `
    <div class="saving-item">
      <strong>${key.replaceAll("_", " ")}</strong>
      <p>${money(value)} estimated annual savings</p>
    </div>
  `).join("");

  $("reportPreview").textContent = JSON.stringify({
    summary: report.summary,
    saved_outputs: report.saved_outputs,
    top_actions: report.action_queue.slice(0, 3),
  }, null, 2);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $(`tab-${button.dataset.tab}`).classList.add("active");
  });
});

$("loadSample").addEventListener("click", async () => {
  try {
    const data = await api("/api/sample");
    state.transactions = data.transactions;
    renderTransactions();
    setMetadata(`Loaded ${data.metadata.transaction_count} sample transactions.`);
  } catch (error) {
    setMetadata(error.message);
  }
});

$("parseCsv").addEventListener("click", async () => {
  try {
    const data = await api("/api/parse-csv", { csv: $("csvInput").value });
    state.transactions = data.transactions;
    renderTransactions();
    setMetadata(`Parsed ${data.metadata.transaction_count} transactions. Columns: ${JSON.stringify(data.metadata.detected_columns)}`);
  } catch (error) {
    setMetadata(error.message);
  }
});

$("parseText").addEventListener("click", async () => {
  try {
    const data = await api("/api/parse-text", { text: $("textInput").value });
    state.transactions = [...state.transactions, ...data.transactions];
    renderTransactions();
    setMetadata(`Extracted ${data.metadata.transaction_count} transactions from pasted text. Rejected lines: ${data.metadata.rejected_lines.length}`);
  } catch (error) {
    setMetadata(error.message);
  }
});

$("addManual").addEventListener("click", () => {
  const merchant = $("manualMerchant").value.trim();
  const amount = Number($("manualAmount").value);
  if (!merchant || !amount) {
    setMetadata("Manual entry needs at least merchant and amount.");
    return;
  }
  state.manualSubscriptions.push({
    merchant,
    amount,
    cadence: $("manualCadence").value,
    next_renewal: $("manualRenewal").value,
    category: $("manualCategory").value.trim() || "uncategorized",
    notes: $("manualNotes").value.trim(),
  });
  renderTransactions();
  setMetadata(`Added manual subscription: ${merchant}.`);
});

$("runAnalysis").addEventListener("click", async () => {
  try {
    const report = await api("/api/analyze", {
      transactions: state.transactions,
      manual_subscriptions: state.manualSubscriptions,
      today: "2026-04-29",
    });
    state.report = report;
    renderReport(report);
    setMetadata("Analysis complete. Reports saved locally in outputs/.");
  } catch (error) {
    setMetadata(error.message);
  }
});

renderTransactions();

