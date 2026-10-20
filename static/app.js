// PricePilot AI — Client-side Application Logic

let productsData = [];
let customersData = [];
let currentRecommendation = null;
let currentSavedQuoteId = null;
let simChart = null;
let winLossChart = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  lucide.createIcons();
  await loadInitialData();
  initSimulator();
  loadDocumentsList();
  loadQuotationsTable();
  loadAnalytics();
});

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-tab").forEach(el => el.classList.remove("active"));

  const targetSection = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);

  if (targetSection) targetSection.classList.remove("hidden");
  if (targetBtn) targetBtn.classList.add("active");

  lucide.createIcons();

  if (tabId === "auditor") {
    loadAuditorData();
  } else if (tabId === "simulator") {
    runSimulation();
  } else if (tabId === "analytics") {
    loadAnalytics();
  } else if (tabId === "documents") {
    loadDocumentsList();
  } else if (tabId === "quotes") {
    loadQuotationsTable();
  } else if (tabId === "evaluate") {
    runEvaluationBenchmarks();
  }
}

// 1. Initial Data Loading
async function loadInitialData() {
  try {
    const [pRes, cRes] = await Promise.all([
      fetch("/api/products"),
      fetch("/api/customers")
    ]);

    productsData = await pRes.json();
    customersData = await cRes.json();

    populateSelects();
    renderCatalog();
  } catch (err) {
    console.error("Error loading initial data:", err);
  }
}

function populateSelects() {
  const custSelect = document.getElementById("input-customer");
  const prodSelect = document.getElementById("input-product");

  custSelect.innerHTML = "";
  prodSelect.innerHTML = "";

  customersData.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.customer_id;
    opt.textContent = `${c.name} (${c.tier} Tier)`;
    custSelect.appendChild(opt);
  });

  productsData.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.sku;
    opt.textContent = `${p.sku} - ${p.name}`;
    prodSelect.appendChild(opt);
  });

  custSelect.addEventListener("change", updateCustomerLabels);
  prodSelect.addEventListener("change", updateProductLabels);

  updateCustomerLabels();
  updateProductLabels();
}

function updateCustomerLabels() {
  const cId = document.getElementById("input-customer").value;
  const c = customersData.find(x => x.customer_id === cId);
  if (c) {
    document.getElementById("lbl-cust-tier").textContent = `${c.tier} Tier`;
    document.getElementById("lbl-cust-terms").textContent = c.credit_terms;
  }
}

function updateProductLabels() {
  const sku = document.getElementById("input-product").value;
  const p = productsData.find(x => x.sku === sku);
  if (p) {
    document.getElementById("lbl-prod-cost").textContent = `₹${parseFloat(p.unit_cost).toFixed(2)}`;
    document.getElementById("lbl-prod-stock").textContent = `${p.current_stock.toLocaleString()} ${p.uom}`;
    document.getElementById("lbl-uom").textContent = p.uom;
  }
}

function setQty(val) {
  document.getElementById("input-quantity").value = val;
}

function fillDemoQuote(custId, prodSku, qty) {
  document.getElementById("input-customer").value = custId;
  document.getElementById("input-product").value = prodSku;
  document.getElementById("input-quantity").value = qty;
  updateCustomerLabels();
  updateProductLabels();
  executeRecommendation();
}

// 2. Natural Language Query Handler
async function handleNlSubmit() {
  const input = document.getElementById("nl-query-input");
  const query = input.value.trim();
  if (!query) return;

  const btn = document.getElementById("btn-run-rec");
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Analyzing Evidence & Computing Floor...`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/copilot/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ natural_language_query: query })
    });
    const data = await res.json();
    currentRecommendation = data;

    // Sync input selectors to parsed entities
    document.getElementById("input-customer").value = data.pricing.customer_id;
    document.getElementById("input-product").value = data.pricing.product_sku;
    document.getElementById("input-quantity").value = data.pricing.quantity;
    updateCustomerLabels();
    updateProductLabels();

    renderRecommendation(data);
  } catch (err) {
    alert("Error executing Copilot request: " + err.message);
  } finally {
    btn.innerHTML = `<i data-lucide="calculator" class="w-4 h-4"></i> Calculate Evidence-Backed Price`;
    lucide.createIcons();
  }
}

// 3. Structured Copilot Execution
async function executeRecommendation() {
  const customerId = document.getElementById("input-customer").value;
  const productSku = document.getElementById("input-product").value;
  const quantity = parseInt(document.getElementById("input-quantity").value) || 100;
  const notes = document.getElementById("input-notes").value;

  const btn = document.getElementById("btn-run-rec");
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Retrieving Evidence & Calculating...`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/copilot/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: customerId,
        product_sku: productSku,
        quantity: quantity,
        user_notes: notes
      })
    });
    const data = await res.json();
    currentRecommendation = data;
    renderRecommendation(data);
  } catch (err) {
    alert("Error executing Copilot recommendation: " + err.message);
  } finally {
    btn.innerHTML = `<i data-lucide="calculator" class="w-4 h-4"></i> Calculate Evidence-Backed Price`;
    lucide.createIcons();
  }
}

function renderRecommendation(data) {
  document.getElementById("results-placeholder").classList.add("hidden");
  document.getElementById("results-container").classList.remove("hidden");

  const p = data.pricing;

  document.getElementById("res-price").textContent = `₹${p.recommended_price.toFixed(2)}`;
  document.getElementById("res-uom").textContent = p.unit_of_measure;
  document.getElementById("res-range").textContent = `₹${p.recommended_range_min.toFixed(2)} – ₹${p.recommended_range_max.toFixed(2)}`;
  document.getElementById("res-margin").textContent = `${p.margin_pct.toFixed(1)}%`;
  document.getElementById("res-profit").textContent = `₹${p.total_profit.toLocaleString()} Order Profit`;
  document.getElementById("res-floor").textContent = `₹${p.price_floor.toFixed(2)}`;
  document.getElementById("res-cost").textContent = `₹${p.effective_unit_cost.toFixed(2)}`;
  document.getElementById("res-list-price").textContent = `₹${p.standard_list_price.toFixed(2)}`;
  document.getElementById("res-discount").textContent = `${p.total_discount_pct.toFixed(1)}%`;

  // Confidence
  document.getElementById("res-conf-score").textContent = `${data.confidence_score}/100`;
  document.getElementById("res-conf-tier").textContent = data.confidence_tier;

  // Active Warnings
  const warnContainer = document.getElementById("res-warnings-container");
  warnContainer.innerHTML = "";
  if (data.warnings && data.warnings.length > 0) {
    data.warnings.forEach(w => {
      const isDanger = w.includes("Conflict") || w.includes("Shortage") || w.includes("outdated");
      const div = document.createElement("div");
      div.className = isDanger 
        ? "bg-amber-50 border border-amber-200 text-amber-900 px-3 py-2 rounded-lg text-xs flex items-center gap-2"
        : "bg-blue-50 border border-blue-200 text-blue-900 px-3 py-2 rounded-lg text-xs flex items-center gap-2";
      div.innerHTML = `
        <i data-lucide="${isDanger ? 'alert-triangle' : 'info'}" class="w-4 h-4 ${isDanger ? 'text-amber-600' : 'text-blue-600'} flex-shrink-0"></i>
        <span>${w}</span>
      `;
      warnContainer.appendChild(div);
    });
  }

  // Explanation
  const expContainer = document.getElementById("res-explanation");
  expContainer.innerHTML = "";
  const paras = data.copilot_explanation.split("\n\n");
  paras.forEach(para => {
    const pEl = document.createElement("p");
    // format markdown bold tags
    pEl.innerHTML = para.replace(/\*\*(.*?)\*\*/g, '<b class="text-slate-900">$1</b>');
    expContainer.appendChild(pEl);
  });

  // Evidence Citations Accordion
  const evList = document.getElementById("res-evidence-list");
  evList.innerHTML = "";
  document.getElementById("res-evidence-count").textContent = `${data.evidence.length} Sources Retrieved`;

  data.evidence.forEach(ev => {
    let badgeClass = "bg-emerald-100 text-emerald-800 border-emerald-200";
    if (ev.status.includes("SUPERSEDED") || ev.status.includes("OUTDATED")) {
      badgeClass = "bg-rose-100 text-rose-800 border-rose-200";
    } else if (ev.status.includes("CONFLICT")) {
      badgeClass = "bg-amber-100 text-amber-800 border-amber-200";
    }

    const item = document.createElement("div");
    item.className = "bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1.5 hover:border-slate-300 transition";
    item.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-slate-800 flex items-center gap-1.5">
          <i data-lucide="file-text" class="w-3.5 h-3.5 text-blue-600"></i>
          ${ev.title}
        </span>
        <div class="flex items-center gap-2">
          <span class="text-[10px] px-2 py-0.5 rounded-full font-semibold border ${badgeClass}">
            ${ev.status}
          </span>
          <span class="text-slate-400 text-[10px]">Date: ${ev.date_issued}</span>
        </div>
      </div>
      <p class="text-slate-600 font-mono text-[11px] bg-white p-2 rounded border border-slate-200/60 leading-relaxed">
        "${ev.snippet}"
      </p>
    `;
    evList.appendChild(item);
  });

  lucide.createIcons();
}

// 4. Human-In-The-Loop Approval & Save
async function approveQuotation() {
  if (!currentRecommendation) return;

  const p = currentRecommendation.pricing;
  try {
    const res = await fetch("/api/quotations/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: p.customer_id,
        product_sku: p.product_sku,
        quantity: p.quantity,
        final_quoted_price: p.recommended_price,
        status: "Approved",
        confidence_score: currentRecommendation.confidence_score,
        citations: currentRecommendation.evidence,
        warnings: currentRecommendation.warnings,
        copilot_explanation: currentRecommendation.copilot_explanation
      })
    });
    const result = await res.json();
    currentSavedQuoteId = result.quote_id;

    alert(`✅ Quotation ${result.quote_number} Approved! Ready for one-click PDF export.`);
    loadQuotationsTable();
    loadAnalytics();
  } catch (err) {
    alert("Error approving quotation: " + err.message);
  }
}

function openOverrideModal() {
  if (!currentRecommendation) return;
  const p = currentRecommendation.pricing;

  document.getElementById("modal-rec-price").textContent = `₹${p.recommended_price.toFixed(2)}`;
  document.getElementById("modal-floor-price").textContent = `₹${p.price_floor.toFixed(2)}`;
  document.getElementById("modal-override-input").value = p.recommended_price.toFixed(2);
  checkModalFloorValidation();

  document.getElementById("modal-override").classList.remove("hidden");
  lucide.createIcons();
}

function closeOverrideModal() {
  document.getElementById("modal-override").classList.add("hidden");
}

function checkModalFloorValidation() {
  if (!currentRecommendation) return;
  const inputVal = parseFloat(document.getElementById("modal-override-input").value) || 0;
  const floorVal = currentRecommendation.pricing.price_floor;
  const warningEl = document.getElementById("modal-floor-warning");
  const btnConfirm = document.getElementById("modal-btn-confirm");

  if (inputVal < floorVal) {
    warningEl.textContent = `⚠️ Below Floor Price (₹${floorVal.toFixed(2)})! Requires explicit override reason.`;
    warningEl.classList.remove("hidden");
  } else {
    warningEl.classList.add("hidden");
  }
}

async function submitOverride() {
  if (!currentRecommendation) return;
  const overridePrice = parseFloat(document.getElementById("modal-override-input").value);
  const reason = document.getElementById("modal-reason-select").value;
  const notes = document.getElementById("modal-notes-input").value;

  const p = currentRecommendation.pricing;

  try {
    const res = await fetch("/api/quotations/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: p.customer_id,
        product_sku: p.product_sku,
        quantity: p.quantity,
        final_quoted_price: overridePrice,
        status: "Overridden",
        override_reason: reason,
        override_notes: notes,
        confidence_score: currentRecommendation.confidence_score,
        citations: currentRecommendation.evidence,
        warnings: currentRecommendation.warnings,
        copilot_explanation: currentRecommendation.copilot_explanation
      })
    });
    const result = await res.json();
    currentSavedQuoteId = result.quote_id;

    closeOverrideModal();
    alert(`Quotation successfully recorded with status 'Overridden' at ₹${overridePrice.toFixed(2)}.`);
    loadQuotationsTable();
    loadAnalytics();
  } catch (err) {
    alert("Error saving override: " + err.message);
  }
}

// 5. One-Click PDF Export
async function downloadCurrentPdf() {
  if (!currentSavedQuoteId) {
    // If not yet saved, approve and save first
    await approveQuotation();
  }
  if (currentSavedQuoteId) {
    window.open(`/api/quotations/${currentSavedQuoteId}/pdf`, "_blank");
  }
}

function downloadQuotePdf(quoteId) {
  window.open(`/api/quotations/${quoteId}/pdf`, "_blank");
}

// 6. AI Quotation Auditor Logic (The Viva Star Feature)
async function loadAuditorData() {
  try {
    const res = await fetch("/api/audit/run?product_sku=HTB-M12-50&customer_id=CUST-001&quantity=500");
    const data = await res.json();

    document.getElementById("audit-sku-name").textContent = `${data.product_sku} (${data.product_name})`;
    document.getElementById("audit-cust-name").textContent = data.customer_name;
    document.getElementById("audit-latest-cost").textContent = `₹${data.supplier_cost_latest.toFixed(2)}`;
    document.getElementById("audit-latest-title").textContent = data.latest_quote_title;
    document.getElementById("audit-suggested-price").textContent = `₹${data.suggested_selling_price.toFixed(2)}`;
    document.getElementById("audit-floor-price").textContent = `₹${data.price_floor.toFixed(2)}`;
    document.getElementById("audit-margin-pct").textContent = `${data.expected_margin_pct.toFixed(1)}%`;

    // Detected Issues List
    const issuesContainer = document.getElementById("audit-issues-list");
    issuesContainer.innerHTML = "";

    data.detected_issues.forEach(issue => {
      let borderClass = "border-slate-200 bg-slate-50";
      let textClass = "text-slate-800";
      if (issue.severity === "High") {
        borderClass = "border-rose-200 bg-rose-50/50";
        textClass = "text-rose-900";
      } else if (issue.severity === "Success") {
        borderClass = "border-emerald-200 bg-emerald-50/50";
        textClass = "text-emerald-900";
      }

      const card = document.createElement("div");
      card.className = `p-4 rounded-xl border ${borderClass} space-y-1 text-xs`;
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold flex items-center gap-1.5 ${textClass}">
            <i data-lucide="${issue.icon}" class="w-4 h-4"></i>
            ${issue.issue_type}
          </span>
          <span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
            Audit Level: ${issue.severity}
          </span>
        </div>
        <p class="text-slate-600 leading-relaxed pl-5">${issue.description}</p>
      `;
      issuesContainer.appendChild(card);
    });

    // Policy Evidence
    document.getElementById("audit-policy-title").textContent = data.policy_evidence.document_title;
    document.getElementById("audit-policy-date").textContent = data.policy_evidence.effective_date;
    document.getElementById("audit-policy-clause").textContent = data.policy_evidence.relevant_clause;

    lucide.createIcons();
  } catch (err) {
    console.error("Error loading auditor data:", err);
  }
}

async function approveFromAuditor() {
  currentRecommendation = {
    pricing: {
      customer_id: "CUST-001",
      product_sku: "HTB-M12-50",
      quantity: 500,
      recommended_price: 20.98,
      price_floor: 20.06,
      effective_unit_cost: 18.40
    },
    confidence_score: 95,
    evidence: [{ title: "Tata Steel Oct 2026 Notice", date_issued: "2026-10-01", status: "ACTIVE" }],
    warnings: ["Audited and approved via AI Quotation Auditor"],
    copilot_explanation: "Audited multi-document quotation approved by Commercial Operations Manager."
  };
  await approveQuotation();
}

// 7. What-If Pricing Simulator
function initSimulator() {
  const ctx = document.getElementById("sim-chart").getContext("2d");
  simChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Direct Cost", "Gross Profit", "Customer Discount"],
      datasets: [{
        label: "Value (₹)",
        data: [18.40, 3.05, 1.37],
        backgroundColor: ["#94A3B8", "#10B981", "#F43F5E"],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "#F1F5F9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

async function runSimulation() {
  const qty = parseInt(document.getElementById("sim-slider-qty").value);
  const cost = parseFloat(document.getElementById("sim-slider-cost").value);
  const margin = parseFloat(document.getElementById("sim-slider-margin").value);
  const discount = parseFloat(document.getElementById("sim-slider-discount").value);

  document.getElementById("sim-val-qty").textContent = `${qty.toLocaleString()} units`;
  document.getElementById("sim-val-cost").textContent = `₹${cost.toFixed(2)}`;
  document.getElementById("sim-val-margin").textContent = `${margin.toFixed(1)}%`;
  document.getElementById("sim-val-discount").textContent = `${discount.toFixed(1)}%`;

  try {
    const res = await fetch("/api/copilot/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_sku: "HTB-M12-50",
        customer_tier: "Platinum",
        quantity: qty,
        supplier_cost: cost,
        discount_pct: discount,
        target_margin_pct: margin
      })
    });
    const data = await res.json();

    document.getElementById("sim-out-price").textContent = `₹${data.simulated_price.toFixed(2)}`;
    document.getElementById("sim-out-unitprofit").textContent = `Profit: ₹${data.profit_per_unit.toFixed(2)} / unit`;
    document.getElementById("sim-out-floor").textContent = `₹${data.price_floor.toFixed(2)}`;
    document.getElementById("sim-out-margin").textContent = `${data.margin_pct.toFixed(1)}%`;
    document.getElementById("sim-out-profit").textContent = `₹${data.total_profit.toLocaleString()}`;
    document.getElementById("sim-out-revenue").textContent = `Revenue: ₹${data.total_revenue.toLocaleString()}`;

    const floorCard = document.getElementById("sim-floor-card");
    const floorStatus = document.getElementById("sim-floor-status");
    const warnBanner = document.getElementById("sim-warning-banner");

    if (data.is_floor_compliant) {
      floorCard.className = "bg-slate-50 border border-slate-200 rounded-xl p-4";
      floorStatus.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i> Floor Compliant`;
      floorStatus.className = "text-[11px] font-semibold text-emerald-600 flex items-center gap-1";
      warnBanner.classList.add("hidden");
    } else {
      floorCard.className = "bg-rose-50 border border-rose-300 rounded-xl p-4";
      floorStatus.innerHTML = `<i data-lucide="alert-octagon" class="w-3.5 h-3.5"></i> Floor Breached! (-₹${data.floor_deficit.toFixed(2)})`;
      floorStatus.className = "text-[11px] font-bold text-rose-600 flex items-center gap-1";
      warnBanner.classList.remove("hidden");
      document.getElementById("sim-warning-text").textContent = data.warning;
    }

    // Update Chart
    if (simChart) {
      const discountAmount = (data.base_price * (discount / 100)).toFixed(2);
      simChart.data.datasets[0].data = [
        cost,
        Math.max(0, data.profit_per_unit),
        discountAmount
      ];
      simChart.update();
    }

    lucide.createIcons();
  } catch (err) {
    console.error("Simulation error:", err);
  }
}

// 8. Document Knowledge Base & Upload
async function loadDocumentsList() {
  try {
    const res = await fetch("/api/documents");
    const docs = await res.json();

    document.getElementById("docs-count-label").textContent = `${docs.length} Documents`;
    const container = document.getElementById("docs-list-container");
    container.innerHTML = "";

    docs.forEach(doc => {
      let badge = `<span class="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-200">ACTIVE</span>`;
      if (doc.is_active === 0 || doc.superseded_by_id) {
        badge = `<span class="bg-rose-100 text-rose-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-rose-200">OUTDATED / SUPERSEDED</span>`;
      } else if (doc.is_conflicting === 1) {
        badge = `<span class="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-200">CONFLICT DETECTED</span>`;
      }

      const card = document.createElement("div");
      card.className = "bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-xs hover:border-slate-300 transition";
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-800 flex items-center gap-1.5">
            <i data-lucide="file" class="w-3.5 h-3.5 text-blue-600"></i>
            ${doc.title}
          </span>
          ${badge}
        </div>
        <div class="flex items-center gap-3 text-[11px] text-slate-400">
          <span>Type: <b>${doc.doc_type}</b></span>
          <span>Issued: <b>${doc.date_issued}</b></span>
          <span>Valid: <b>${doc.valid_until || 'N/A'}</b></span>
        </div>
        <p class="text-slate-600 text-[11px] leading-relaxed">${doc.summary || ''}</p>
      `;
      container.appendChild(card);
    });

    lucide.createIcons();
  } catch (err) {
    console.error("Error loading documents:", err);
  }
}

async function handleDocumentUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById("upload-file");
  const titleInput = document.getElementById("upload-title");
  const typeSelect = document.getElementById("upload-type");
  const statusDiv = document.getElementById("upload-status");

  if (!fileInput.files || fileInput.files.length === 0) return;

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);
  if (titleInput.value) formData.append("title", titleInput.value);
  formData.append("doc_type", typeSelect.value);

  const btn = document.getElementById("btn-upload");
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Ingesting & Re-indexing RAG...`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/documents/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    statusDiv.className = "text-xs p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 block";
    statusDiv.innerHTML = `
      <b>Success!</b> ${data.message}<br/>
      <span class="text-[11px] text-emerald-700">Identified Type: ${data.doc_type} | Extracted Date: ${data.date_issued} | Price Mention: ₹${data.extracted_price || 'N/A'}</span>
    `;

    fileInput.value = "";
    titleInput.value = "";
    loadDocumentsList();
    loadInitialData(); // update product costs if modified
  } catch (err) {
    statusDiv.className = "text-xs p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 block";
    statusDiv.textContent = "Upload failed: " + err.message;
  } finally {
    btn.innerHTML = `<i data-lucide="upload" class="w-3.5 h-3.5"></i> Extract, Analyze & Ingest into RAG`;
    lucide.createIcons();
  }
}

// 9. Quotations Pipeline Table
async function loadQuotationsTable() {
  try {
    const res = await fetch("/api/quotations");
    const quotes = await res.json();

    const tbody = document.getElementById("quotes-table-body");
    tbody.innerHTML = "";

    quotes.forEach(q => {
      let statusBadge = `<span class="bg-slate-100 text-slate-800 px-2 py-0.5 rounded font-semibold text-[10px]">${q.status}</span>`;
      if (q.status === "Approved") statusBadge = `<span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-semibold text-[10px]">Approved</span>`;
      if (q.status === "Overridden") statusBadge = `<span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-semibold text-[10px]">Overridden</span>`;

      let outcomeBadge = `<span class="text-slate-400">Pending</span>`;
      if (q.won_lost_outcome === "Won") outcomeBadge = `<span class="text-emerald-600 font-bold">Won ✓</span>`;
      if (q.won_lost_outcome === "Lost") outcomeBadge = `<span class="text-rose-600 font-bold">Lost ✗</span>`;

      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-mono font-semibold text-blue-600">${q.quote_number}</td>
        <td class="py-2.5 px-3 font-medium">${q.customer_name}</td>
        <td class="py-2.5 px-3 font-mono">${q.product_sku}</td>
        <td class="py-2.5 px-3">${q.quantity.toLocaleString()}</td>
        <td class="py-2.5 px-3 font-bold">₹${parseFloat(q.final_quoted_price).toFixed(2)}</td>
        <td class="py-2.5 px-3 font-semibold text-emerald-600">${parseFloat(q.margin_pct).toFixed(1)}%</td>
        <td class="py-2.5 px-3">${statusBadge}</td>
        <td class="py-2.5 px-3">${outcomeBadge}</td>
        <td class="py-2.5 px-3 text-right">
          <button onclick="downloadQuotePdf('${q.quote_id}')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded text-[11px] font-semibold transition inline-flex items-center gap-1">
            <i data-lucide="download" class="w-3 h-3"></i> PDF
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    lucide.createIcons();
  } catch (err) {
    console.error("Error loading quotations:", err);
  }
}

// 10. Historical Analytics & Statistical Learning
async function loadAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    const data = await res.json();

    document.getElementById("stat-win-rate").textContent = `${data.overall_win_rate_pct}%`;
    document.getElementById("stat-won-margin").textContent = `${data.avg_won_margin_pct}%`;
    document.getElementById("stat-lost-margin").textContent = `${data.avg_lost_margin_pct}%`;
    document.getElementById("stat-total-quotes").textContent = data.total_quotations;

    // Strategic Insights
    const insContainer = document.getElementById("analytics-insights-container");
    insContainer.innerHTML = "";

    data.strategic_insights.forEach(ins => {
      let iconColor = "text-blue-600";
      let bg = "bg-blue-50/50 border-blue-200";
      if (ins.type === "positive") {
        iconColor = "text-emerald-600";
        bg = "bg-emerald-50/50 border-emerald-200";
      } else if (ins.type === "warning") {
        iconColor = "text-amber-600";
        bg = "bg-amber-50/50 border-amber-200";
      }

      const card = document.createElement("div");
      card.className = `p-3.5 rounded-xl border ${bg} text-xs space-y-1`;
      card.innerHTML = `
        <span class="font-bold flex items-center gap-1.5 ${iconColor}">
          <i data-lucide="info" class="w-3.5 h-3.5"></i>
          ${ins.title}
        </span>
        <p class="text-slate-600 leading-relaxed">${ins.insight}</p>
      `;
      insContainer.appendChild(card);
    });

    // Chart.js Win/Loss
    const ctx = document.getElementById("chart-win-loss").getContext("2d");
    if (winLossChart) winLossChart.destroy();

    const labels = data.discount_brackets.map(b => b.bracket);
    const winRates = data.discount_brackets.map(b => b.win_rate);

    winLossChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Win Rate (%)",
          data: winRates,
          backgroundColor: "#3B82F6",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, max: 100, grid: { color: "#F1F5F9" } },
          x: { grid: { display: false } }
        }
      }
    });

    lucide.createIcons();
  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

// 11. Benchmark Experiments (Section 8)
async function runEvaluationBenchmarks() {
  const btn = document.getElementById("btn-run-eval");
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Executing Benchmark Tests...`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/evaluate");
    const data = await res.json();

    // Top Metrics Grid
    const grid = document.getElementById("eval-metrics-grid");
    grid.innerHTML = "";

    const metricsKeys = ["turnaround_time", "constraint_adherence", "stale_data_detection", "evidence_traceability"];
    metricsKeys.forEach(key => {
      const m = data.metrics[key];
      const card = document.createElement("div");
      card.className = "bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-2 text-xs";
      card.innerHTML = `
        <span class="font-bold text-slate-500 uppercase tracking-wider block">${m.metric}</span>
        <div class="space-y-1">
          <div class="flex justify-between">
            <span class="text-slate-400">Baseline Rule:</span>
            <span class="font-semibold text-slate-700">${m.baseline}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-purple-600 font-bold">PricePilot AI:</span>
            <span class="font-extrabold text-purple-700">${m.pricepilot}</span>
          </div>
        </div>
        <div class="pt-2 border-t border-slate-200">
          <span class="px-2 py-0.5 rounded font-bold text-[10px] bg-emerald-100 text-emerald-800">
            ${m.improvement}
          </span>
        </div>
      `;
      grid.appendChild(card);
    });

    // Scenarios Table
    const tbody = document.getElementById("eval-scenarios-body");
    tbody.innerHTML = "";

    data.detailed_scenarios.forEach(sc => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-mono font-bold text-purple-700">${sc.scenario_id}</td>
        <td class="py-2.5 px-3">
          <span class="font-semibold text-slate-800 block">${sc.scenario_name}</span>
          <span class="text-[10px] text-slate-400">${sc.customer} • ${sc.quantity} units</span>
        </td>
        <td class="py-2.5 px-3 font-mono">
          <span class="font-semibold">₹${sc.baseline_quote.price.toFixed(2)}</span>
          <span class="text-[10px] text-slate-400 block">${sc.baseline_quote.method}</span>
        </td>
        <td class="py-2.5 px-3 font-mono text-blue-700 font-bold">
          ₹${sc.pricepilot_quote.price.toFixed(2)}
          <span class="text-[10px] text-emerald-600 block">${sc.pricepilot_quote.margin_pct.toFixed(1)}% Margin</span>
        </td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${sc.pricepilot_quote.floor_compliant ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
            ${sc.pricepilot_quote.floor_compliant ? '100% Compliant' : 'Breached'}
          </span>
        </td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${sc.pricepilot_quote.stale_data_detected ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-600'}">
            ${sc.pricepilot_quote.stale_data_detected ? 'Alert Triggered' : 'N/A'}
          </span>
        </td>
        <td class="py-2.5 px-3 font-mono text-slate-500">${sc.execution_time_ms} ms</td>
      `;
      tbody.appendChild(tr);
    });

    lucide.createIcons();
  } catch (err) {
    alert("Evaluation run failed: " + err.message);
  } finally {
    btn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i> Run Live Experiments`;
    lucide.createIcons();
  }
}

// 12. Catalog Rendering
function renderCatalog() {
  const pBody = document.getElementById("catalog-products-body");
  const cBody = document.getElementById("catalog-customers-body");

  pBody.innerHTML = "";
  cBody.innerHTML = "";

  productsData.forEach(p => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition";
    tr.innerHTML = `
      <td class="py-2 px-3 font-mono font-semibold text-blue-600">${p.sku}</td>
      <td class="py-2 px-3 font-medium">${p.name}</td>
      <td class="py-2 px-3 font-bold">₹${parseFloat(p.unit_cost).toFixed(2)}</td>
      <td class="py-2 px-3 text-emerald-600 font-semibold">${p.current_stock.toLocaleString()} ${p.uom}</td>
      <td class="py-2 px-3 font-mono text-slate-400">${p.hsn_code}</td>
    `;
    pBody.appendChild(tr);
  });

  customersData.forEach(c => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition";
    tr.innerHTML = `
      <td class="py-2 px-3 font-medium">${c.name}</td>
      <td class="py-2 px-3"><span class="font-bold text-blue-600">${c.tier}</span></td>
      <td class="py-2 px-3 text-slate-600">${c.credit_terms}</td>
      <td class="py-2 px-3 text-slate-500">${c.price_sensitivity}</td>
    `;
    cBody.appendChild(tr);
  });

  lucide.createIcons();
}
