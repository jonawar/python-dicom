"use strict";

const $ = (id) => document.getElementById(id);

const LIMITS = { max_per_date: 200, max_dates: 366, max_total: 3000 };
const CONFIRM_THRESHOLD = 300;

const state = {
  options: null,
  records: [],
  currentJob: null,
  pollTimer: null,
  search: "",
  dateFilter: "",
};

/* ---------- helpers ---------- */

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtDate(yymmdd) {
  if (!yymmdd || yymmdd.length !== 8) return yymmdd || "-";
  return `${yymmdd.slice(6, 8)}/${yymmdd.slice(4, 6)}/${yymmdd.slice(0, 4)}`;
}

function fmtTime(hhmmss) {
  if (!hhmmss || hhmmss.length < 4) return "";
  return `${hhmmss.slice(0, 2)}:${hhmmss.slice(2, 4)}`;
}

function fmtBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function toast(msg, isError = false) {
  const box = $("toasts");
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " error" : "");
  const icon = isError
    ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4m0 4h.01"/></svg>'
    : '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 4.5-5"/></svg>';
  el.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHtml(msg)}</span>`;
  box.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    el.addEventListener("animationend", () => el.remove());
  }, 4200);
}

function confirmDialog(title, body) {
  return new Promise((resolve) => {
    $("modal-title").textContent = title;
    $("modal-body").textContent = body;
    $("modal-backdrop").classList.remove("hidden");
    const yes = $("modal-yes"), no = $("modal-no"), backdrop = $("modal-backdrop");
    const close = (val) => {
      backdrop.classList.add("hidden");
      yes.onclick = no.onclick = backdrop.onclick = null;
      resolve(val);
    };
    yes.onclick = () => close(true);
    no.onclick = () => close(false);
    backdrop.onclick = (e) => { if (e.target === backdrop) close(false); };
  });
}

/* ---------- select population ---------- */

function fillSelect(id, values, allLabel, includeRandom = true) {
  const sel = $(id);
  sel.innerHTML = "";
  if (includeRandom) {
    const o = document.createElement("option");
    o.value = "random";
    o.textContent = `Acak (${allLabel})`;
    sel.appendChild(o);
  }
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  }
}

function populateOptions() {
  const o = state.options;
  Object.assign(LIMITS, o.limits);
  fillSelect("sel-modality", o.modalities, "semua modality");
  fillSelect("sel-location", o.locations, "semua lokasi");
  fillSelect("sel-institution", o.institutions, "semua RS");
  fillSelect("sel-department", o.departments, "semua departemen", false);
  fillSelect("sel-guarantor", o.guarantors, "semua penjamin");
  $("inp-count").max = LIMITS.max_per_date;
}

/* ---------- summary ---------- */

function daysBetween(a, b) {
  const d0 = new Date(a), d1 = new Date(b);
  if (!a || !b || isNaN(d0) || isNaN(d1)) return 0;
  return Math.round(Math.abs(d1 - d0) / 86400000) + 1;
}

function getFormConfig() {
  return {
    count_per_date: Math.max(1, parseInt($("inp-count").value, 10) || 1),
    start_date: $("inp-start").value,
    end_date: $("inp-end").value || $("inp-start").value,
    modality: $("sel-modality").value,
    location: $("sel-location").value,
    institution: $("sel-institution").value,
    department: $("sel-department").value,
    guarantor: $("sel-guarantor").value,
    patient_sex: $("sel-sex").value,
    image_style: $("sel-image").value,
    output_dir: $("inp-outdir").value.trim() || "generated_dicoms",
  };
}

function updateSummary() {
  const cfg = getFormConfig();
  const days = daysBetween(cfg.start_date, cfg.end_date);
  const total = days * cfg.count_per_date;
  $("sum-dates").textContent = days;
  $("sum-per").textContent = cfg.count_per_date;
  $("sum-total").textContent = total;

  const warn = $("summary-warn");
  let msg = "";
  if (days === 0) msg = "Pilih rentang tanggal yang valid.";
  else if (cfg.count_per_date > LIMITS.max_per_date) msg = `Maksimal ${LIMITS.max_per_date} file per tanggal.`;
  else if (days > LIMITS.max_dates) msg = `Rentang maksimal ${LIMITS.max_dates} hari.`;
  else if (total > LIMITS.max_total) msg = `Total melebihi batas ${LIMITS.max_total} file. Kurangi jumlah atau rentang.`;
  warn.textContent = msg;
  warn.classList.toggle("hidden", !msg);
  $("btn-generate").disabled = !!msg;
}

/* ---------- results table ---------- */

function uniqueDates(records) {
  return [...new Set(records.map((r) => r.ScheduledDate))].sort().reverse();
}

function renderTable() {
  const tbody = $("results-body");
  const q = state.search.toLowerCase();
  const rows = state.records.filter((r) => {
    if (state.dateFilter && r.ScheduledDate !== state.dateFilter) return false;
    if (!q) return true;
    return (
      r.PatientID.toLowerCase().includes(q) ||
      r.PatientName.toLowerCase().includes(q) ||
      r.Institution.toLowerCase().includes(q) ||
      r.AccessionNumber.toLowerCase().includes(q) ||
      (r.File || "").toLowerCase().includes(q)
    );
  });

  $("row-count").textContent = `${rows.length} baris`;
  $("results-table").classList.toggle("hidden", rows.length === 0);
  $("empty-state").classList.toggle("hidden", rows.length > 0);

  tbody.innerHTML = rows.map((r, i) => `
    <tr>
      <td class="th-idx">${i + 1}</td>
      <td class="cell-pid">${escapeHtml(r.PatientID)}</td>
      <td class="cell-name">${escapeHtml(r.PatientName)}</td>
      <td><span class="sex-${escapeHtml(r.PatientSex)}">${escapeHtml(r.PatientSex)}</span></td>
      <td>${fmtDate(r.PatientBirthDate)}</td>
      <td>${fmtDate(r.ScheduledDate)} ${fmtTime(r.ScheduledTime)}</td>
      <td><span class="pill mod-${escapeHtml(r.Modality)}">${escapeHtml(r.Modality)}</span></td>
      <td>${escapeHtml(r.Location)}</td>
      <td>${escapeHtml(r.Institution)}</td>
      <td>${escapeHtml(r.Guarantor)}</td>
      <td class="th-act">
        ${r.File ? `<button class="row-dl" title="Unduh ${escapeHtml(r.File)}" data-file="${escapeHtml(r.File)}">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16"/></svg>
        </button>` : ""}
      </td>
    </tr>`).join("");

  const dates = uniqueDates(state.records);
  const sel = $("sel-filter-date");
  const prev = sel.value;
  sel.innerHTML = '<option value="">Semua tanggal</option>' +
    dates.map((d) => `<option value="${d}">${fmtDate(d)}</option>`).join("");
  sel.value = dates.includes(prev) ? prev : "";
  state.dateFilter = sel.value;
}

async function loadRecords() {
  const dir = $("inp-outdir").value.trim() || "generated_dicoms";
  try {
    const { records } = await api(`/api/records?dir=${encodeURIComponent(dir)}`);
    state.records = records || [];
  } catch (_) {
    state.records = [];
  }
  renderTable();
}

async function refreshSummaryStats() {
  const dir = $("inp-outdir").value.trim() || "generated_dicoms";
  try {
    const s = await api(`/api/summary?dir=${encodeURIComponent(dir)}`);
    $("stat-folder").textContent = s.files;
    $("stat-size").textContent = fmtBytes(s.size);
    $("folder-badge-text").textContent = `${dir} · ${s.files} file`;
  } catch (_) {}
}

/* ---------- generate ---------- */

function setBusy(busy) {
  $("btn-generate").disabled = busy;
  $("btn-generate").innerHTML = busy
    ? '<span class="spinner"></span><span>Sedang membuat...</span>'
    : '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z"/></svg><span>Generate DICOM</span>';
}

function showProgress(show) {
  $("progress-card").classList.toggle("hidden", !show);
}

function updateProgress(j) {
  $("prog-fill").style.width = `${j.percent}%`;
  $("prog-track").setAttribute("aria-valuenow", j.percent);
  $("prog-pct").textContent = `${j.percent}%`;
  $("prog-count").textContent = `${j.done} / ${j.total} file`;
  $("prog-msg").textContent = j.message;
}

async function pollJob(jobId) {
  if (state.currentJob !== jobId) return;
  try {
    const j = await api(`/api/jobs/${jobId}`);
    updateProgress(j);
    if (j.status === "running") {
      state.pollTimer = setTimeout(() => pollJob(jobId), 400);
      return;
    }
    state.currentJob = null;
    setBusy(false);
    if (j.status === "done") {
      const res = await api(`/api/jobs/${jobId}/results`);
      state.records = res.records;
      renderTable();
      $("stat-batch").textContent = state.records.length;
      $("stat-time").textContent = `${j.elapsed}s`;
      refreshSummaryStats();
      showProgress(false);
      toast(`Berhasil membuat ${state.records.length} file DICOM.`);
    } else if (j.status === "cancelled") {
      showProgress(false);
      toast("Generate dibatalkan.", true);
      refreshSummaryStats();
      loadRecords();
    } else {
      showProgress(false);
      toast(j.error || "Terjadi kesalahan saat generate.", true);
    }
  } catch (err) {
    state.pollTimer = setTimeout(() => pollJob(jobId), 1500);
  }
}

async function generate() {
  const cfg = getFormConfig();
  const days = daysBetween(cfg.start_date, cfg.end_date);
  const total = days * cfg.count_per_date;
  if (!days || !cfg.start_date) {
    toast("Pilih rentang tanggal terlebih dahulu.", true);
    return;
  }

  if (total > CONFIRM_THRESHOLD) {
    const ok = await confirmDialog(
      "Konfirmasi generate besar",
      `Anda akan membuat ${total} file DICOM (${cfg.count_per_date} file × ${days} tanggal). Proses bisa memakan waktu beberapa saat. Lanjutkan?`
    );
    if (!ok) return;
  }

  setBusy(true);
  showProgress(true);
  updateProgress({ percent: 0, done: 0, total, message: "Memulai..." });

  try {
    const res = await api("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    state.currentJob = res.job_id;
    pollJob(res.job_id);
  } catch (err) {
    setBusy(false);
    showProgress(false);
    toast(err.message, true);
  }
}

function cancelJob() {
  if (!state.currentJob) return;
  api(`/api/jobs/${state.currentJob}/cancel`, { method: "POST" }).catch(() => {});
}

/* ---------- wiring ---------- */

function wireEvents() {
  $("inp-count").addEventListener("input", () => {
    syncCountChips();
    updateSummary();
  });
  $("count-dec").addEventListener("click", () => nudgeCount(-1));
  $("count-inc").addEventListener("click", () => nudgeCount(1));
  $("count-chips").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-count]");
    if (!btn) return;
    $("inp-count").value = btn.dataset.count;
    syncCountChips();
    updateSummary();
  });

  $("inp-start").addEventListener("change", () => {
    if ($("inp-end").value < $("inp-start").value) $("inp-end").value = $("inp-start").value;
    syncRangeChips();
    updateSummary();
  });
  $("inp-end").addEventListener("change", () => {
    syncRangeChips();
    updateSummary();
  });
  $("range-chips").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-range]");
    if (!btn) return;
    const t = btn.dataset.range;
    const end = new Date();
    let start = new Date();
    if (t === "7") start.setDate(start.getDate() - 6);
    else if (t === "30") start.setDate(start.getDate() - 29);
    $("inp-start").value = isoDate(start);
    $("inp-end").value = isoDate(end);
    syncRangeChips();
    updateSummary();
  });

  $("inp-search").addEventListener("input", (e) => {
    state.search = e.target.value;
    renderTable();
  });
  $("sel-filter-date").addEventListener("change", (e) => {
    state.dateFilter = e.target.value;
    renderTable();
  });

  $("btn-generate").addEventListener("click", generate);
  $("btn-cancel").addEventListener("click", cancelJob);
  $("btn-refresh").addEventListener("click", () => {
    loadRecords();
    refreshSummaryStats();
  });
  $("btn-reset").addEventListener("click", resetForm);

  $("btn-open").addEventListener("click", async () => {
    const dir = $("inp-outdir").value.trim() || "generated_dicoms";
    try {
      await api(`/api/open-folder?dir=${encodeURIComponent(dir)}`, { method: "POST" });
    } catch (err) { toast(err.message, true); }
  });
  $("btn-zip").addEventListener("click", () => {
    const dir = $("inp-outdir").value.trim() || "generated_dicoms";
    window.location = `/api/download-zip?dir=${encodeURIComponent(dir)}`;
  });
  $("btn-json").addEventListener("click", () => {
    const data = JSON.stringify(state.records, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "dicom_data.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  });

  $("results-body").addEventListener("click", (e) => {
    const btn = e.target.closest(".row-dl");
    if (!btn) return;
    const dir = $("inp-outdir").value.trim() || "generated_dicoms";
    window.location = `/api/download/${encodeURIComponent(btn.dataset.file)}?dir=${encodeURIComponent(dir)}`;
  });
}

function nudgeCount(delta) {
  const inp = $("inp-count");
  const v = Math.min(LIMITS.max_per_date, Math.max(1, (parseInt(inp.value, 10) || 1) + delta));
  inp.value = v;
  syncCountChips();
  updateSummary();
}

function syncCountChips() {
  const v = $("inp-count").value;
  document.querySelectorAll("#count-chips .chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.count === v));
}

function syncRangeChips() {
  const s = $("inp-start").value, e = $("inp-end").value, t = todayIso();
  const weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 6);
  const monthAgo = new Date(); monthAgo.setDate(monthAgo.getDate() - 29);
  document.querySelectorAll("#range-chips .chip").forEach((c) => {
    const r = c.dataset.range;
    const active =
      (r === "today" && s === t && e === t) ||
      (r === "7" && s === isoDate(weekAgo) && e === t) ||
      (r === "30" && s === isoDate(monthAgo) && e === t);
    c.classList.toggle("active", active);
  });
}

function resetForm() {
  $("inp-count").value = 10;
  $("inp-start").value = todayIso();
  $("inp-end").value = todayIso();
  $("sel-modality").value = "random";
  $("sel-location").value = "random";
  $("sel-institution").value = "random";
  $("sel-department").selectedIndex = 0;
  $("sel-guarantor").value = "random";
  $("sel-sex").value = "random";
  $("sel-image").value = "gradient";
  $("inp-outdir").value = "generated_dicoms";
  syncCountChips();
  syncRangeChips();
  updateSummary();
}

/* ---------- init ---------- */

async function init() {
  const t = todayIso();
  $("inp-start").value = t;
  $("inp-end").value = t;
  try {
    state.options = await api("/api/options");
    populateOptions();
  } catch (err) {
    toast("Gagal memuat opsi dari server.", true);
  }
  wireEvents();
  syncCountChips();
  syncRangeChips();
  updateSummary();
  await Promise.all([loadRecords(), refreshSummaryStats()]);
  $("stat-batch").textContent = state.records.length;
}

init();
