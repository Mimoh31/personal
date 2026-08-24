let currentUser = null;

function $(id) { return document.getElementById(id); }

function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  $(id).classList.add("active");
}

function showView(name) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".nav-item[data-view]").forEach(n => n.classList.remove("active"));
  $("view-" + name).classList.add("active");
  const nav = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (nav) nav.classList.add("active");

  if (name === "dashboard") loadDashboard();
  if (name === "jobfeed") loadJobs();
  if (name === "board") loadBoard();
  if (name === "inbox") loadInboxStatus();
  if (name === "cv") loadCvWorkspaceJobs();
  if (name === "apply") loadApplyQueue();
}

// --- Auth navigation (login and register are separate pages) ---
$("go-to-register").onclick = (e) => { e.preventDefault(); showScreen("screen-register"); };
$("go-to-login").onclick = (e) => { e.preventDefault(); showScreen("screen-login"); };

$("create-btn").onclick = async () => {
  const username = $("create-username").value.trim();
  const password = $("create-password").value;
  const res = await fetch("/api/accounts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  if (!res.ok) {
    $("create-error").textContent = data.error;
    return;
  }
  $("create-error").textContent = "";
  $("login-username").value = username;
  $("login-password").value = "";
  showScreen("screen-login");
};

$("login-btn").onclick = async () => {
  const username = $("login-username").value.trim();
  const password = $("login-password").value;
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  if (!res.ok) {
    $("login-error").textContent = data.error;
    return;
  }
  $("login-error").textContent = "";
  currentUser = username;
  $("user-label").textContent = username;
  showScreen("screen-main");
  showView("dashboard");
  loadProfile();
  loadCvList();
  loadGuidance();
};

$("logout-btn").onclick = (e) => {
  e.preventDefault();
  currentUser = null;
  showScreen("screen-login");
};

// Any element with data-view (sidebar nav items AND dashboard shortcut tiles)
document.querySelectorAll("[data-view]").forEach(link => {
  link.onclick = (e) => {
    e.preventDefault();
    showView(link.dataset.view);
  };
});

// --- Landing dashboard ---
async function loadDashboard() {
  const res = await fetch(`/api/dashboard-summary/${currentUser}`);
  const s = await res.json();
  $("dashboard-stats").innerHTML = `
    <div class="stat-tile"><span class="stat-num mono">${s.jobsCount}</span><span class="stat-label">Jobs found</span></div>
    <div class="stat-tile"><span class="stat-num mono">${s.shortlisted}</span><span class="stat-label">Shortlisted</span></div>
    <div class="stat-tile"><span class="stat-num mono">${s.cvReady}</span><span class="stat-label">CV ready</span></div>
    <div class="stat-tile"><span class="stat-num mono">${s.applied}</span><span class="stat-label">Applied</span></div>
    <div class="stat-tile"><span class="stat-num mono">${s.guidanceReady ? "\u2713" : "\u2014"}</span><span class="stat-label">Guidance ready</span></div>
  `;
}

// --- Profile load/save ---
async function loadProfile() {
  const res = await fetch(`/api/profile/${currentUser}`);
  const p = await res.json();
  $("linkedin-url").value = p.linkedinUrl || "";
  $("portfolio").value = p.portfolio || "";
  $("work-auth").value = p.workAuth || "citizen";
  $("salary-current").value = p.salaryCurrent || "";
  $("salary-expected").value = p.salaryExpected || "";
  $("relocate").value = p.relocate || "yes";
  $("notice-period").value = p.noticePeriod || "";
  $("guardrails").value = p.guardrails || "";
}

$("save-profile-btn").onclick = async () => {
  const body = {
    linkedinUrl: $("linkedin-url").value.trim(),
    portfolio: $("portfolio").value.trim(),
    workAuth: $("work-auth").value,
    salaryCurrent: $("salary-current").value.trim(),
    salaryExpected: $("salary-expected").value.trim(),
    relocate: $("relocate").value,
    noticePeriod: $("notice-period").value.trim(),
    guardrails: $("guardrails").value.trim()
  };
  await fetch(`/api/profile/${currentUser}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  $("save-status").textContent = "Saved.";
  setTimeout(() => { $("save-status").textContent = ""; }, 2000);
};

// --- CV upload ---
$("cv-upload-btn").onclick = async () => {
  const files = $("cv-files").files;
  if (!files.length) return;
  const form = new FormData();
  for (const f of files) form.append("files", f);
  await fetch(`/api/upload/cv/${currentUser}`, { method: "POST", body: form });
  loadCvList();
};

async function loadCvList() {
  const res = await fetch(`/api/cv-list/${currentUser}`);
  const files = await res.json();
  $("cv-list").innerHTML = files.map(f => `<li>${f}</li>`).join("");
}

// --- LinkedIn upload ---
$("linkedin-upload-btn").onclick = async () => {
  const file = $("linkedin-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api/upload/linkedin/${currentUser}`, { method: "POST", body: form });
  const data = await res.json();
  $("linkedin-status").textContent = res.ok ? `Uploaded: ${data.saved}` : data.error;
};

// --- Guidance (read-only, written by Agent 1) ---
async function loadGuidance() {
  const res = await fetch(`/api/guidance/${currentUser}`);
  const g = await res.json();
  const panel = $("guidance-panel");
  if (!g) {
    panel.innerHTML = `<p class="hint">No guidance yet. Run the agent1-profile-guidance skill in Claude Code after uploading your CVs.</p>`;
    return;
  }
  panel.innerHTML = `
    <p class="hint">Generated ${g.generatedAt}</p>
    <p><strong>Target roles:</strong> ${g.targetRoles.join(", ")}</p>
    <p><strong>Seniority:</strong> ${g.seniority}</p>
    <p><strong>Must-haves:</strong> ${g.mustHaves.join(", ")}</p>
    <p><strong>Deal-breakers:</strong> ${g.dealBreakers.join(", ")}</p>
    <p><strong>Strengths:</strong> ${g.strengths.join(", ")}</p>
    <p><strong>Gaps:</strong> ${g.gaps.join(", ")}</p>
    <p class="hint">${g.notes}</p>
  `;
}

// --- Job feed + Agent 5 run trigger ---
async function loadJobs() {
  const res = await fetch("/api/jobs");
  const jobs = await res.json();
  const list = $("job-list");
  if (!jobs.length) {
    list.innerHTML = `<p class="hint">No jobs yet. Click "Run web search agent" above, or run it yourself in Claude Code.</p>`;
    return;
  }
  list.innerHTML = jobs.map(j => `
    <li>
      <strong>${j.title}</strong> &mdash; ${j.company}
      <span class="tag" style="background:var(--signal-soft);color:var(--signal)">${j.source}</span>
      <br><span class="hint">${j.location || ""}</span>
    </li>
  `).join("");
}

$("run-agent5-btn").onclick = async () => {
  $("agent5-run-status").textContent = "Requesting...";
  const res = await fetch("/api/agent-trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent: "agent5-web-search", username: currentUser })
  });
  const data = await res.json();
  $("agent5-run-status").textContent = res.ok
    ? `Requested. Open your Claude Code session on this folder and say "search for jobs" \u2014 Agent 5 will pick this up (request #${data.queued}).`
    : "Couldn't queue the request.";
};

// --- Ranked board ---
const COLUMNS = ["new", "shortlisted", "cv_ready", "applied"];
const COLUMN_LABELS = { new: "New", shortlisted: "Shortlisted", cv_ready: "CV ready", applied: "Applied" };

async function loadBoard() {
  const res = await fetch("/api/board");
  const board = await res.json();
  const container = $("board-columns");
  container.innerHTML = COLUMNS.map(col => {
    const items = board.filter(b => b.status === col).sort((a, b) => (b.score || 0) - (a.score || 0));
    const cards = items.map(j => `
      <div class="board-card">
        <span class="job-title">${j.title}</span>
        ${j.company || ""}
        <span class="tag" style="background:var(--signal-soft);color:var(--signal)">${j.source}</span>
        ${j.score != null ? `<div class="hint mono">Score: ${j.score}</div>` : ""}
      </div>
    `).join("") || `<p class="hint">Empty</p>`;
    return `<div class="board-col"><h4>${COLUMN_LABELS[col]}</h4>${cards}</div>`;
  }).join("");
}

// --- Add job modal ---
$("open-add-job").onclick = () => {
  $("add-job-modal").classList.remove("hidden");
  $("add-job-url-step").classList.remove("hidden");
  $("add-job-jd-step").classList.add("hidden");
  $("manual-url").value = "";
  $("manual-jd").value = "";
  $("fetch-error").textContent = "";
  $("add-job-status").textContent = "";
};

function closeAddJobModal() {
  $("add-job-modal").classList.add("hidden");
}
$("cancel-add-job").onclick = closeAddJobModal;
$("cancel-add-job-2").onclick = closeAddJobModal;

$("fetch-job-btn").onclick = async () => {
  const url = $("manual-url").value.trim();
  if (!url) {
    $("add-job-status").textContent = "Enter a link, or cancel and paste a JD instead.";
    return;
  }
  $("add-job-status").textContent = "Fetching\u2026";
  const res = await fetch("/api/manual-job/fetch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });
  const data = await res.json();
  $("add-job-status").textContent = "";
  if (data.ok) {
    await fetch("/api/manual-job", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, jdText: data.text })
    });
    closeAddJobModal();
    loadBoard();
  } else {
    $("fetch-error").textContent = "Couldn't fetch that link. Paste the job description instead.";
    $("add-job-url-step").classList.add("hidden");
    $("add-job-jd-step").classList.remove("hidden");
  }
};

$("submit-jd-btn").onclick = async () => {
  const jdText = $("manual-jd").value.trim();
  if (!jdText) {
    $("fetch-error").textContent = "Paste the job description first.";
    return;
  }
  await fetch("/api/manual-job", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: $("manual-url").value.trim(), jdText })
  });
  closeAddJobModal();
  loadBoard();
};

// --- CV workspace ---
async function loadCvWorkspaceJobs() {
  const res = await fetch("/api/board");
  const board = await res.json();
  const eligible = board.filter(j => j.status === "shortlisted" || j.status === "cv_ready");
  const select = $("cv-job-select");
  select.innerHTML = eligible.map(j => `<option value="${j.id}">${j.title} \u2014 ${j.company}</option>`).join("")
    || `<option value="">No shortlisted jobs yet</option>`;
  select.onchange = () => loadCvTailoring(select.value);
  if (eligible.length) loadCvTailoring(eligible[0].id);
  else $("cv-workspace-body").innerHTML = `<p class="hint">Shortlist a job on the Ranked board first.</p>`;
}

async function loadCvTailoring(jobId) {
  if (!jobId) return;
  const res = await fetch(`/api/cv-tailoring/${currentUser}/${jobId}`);
  const t = await res.json();
  const body = $("cv-workspace-body");
  if (!t) {
    body.innerHTML = `<p class="hint">No draft yet. Run the agent7-cv-tailor skill in Claude Code for this job.</p>`;
    return;
  }
  const changesHtml = t.changes.map(c => `
    <div class="row-field"><span style="color:var(--danger)">&minus; Existing: "${c.existing}"</span></div>
    <div class="row-field"><span style="color:var(--signal)">+ Modified: "${c.modified}"</span></div>
  `).join("");
  const isDecided = t.status !== "pending_review";
  body.innerHTML = `
    <div style="background:var(--signal-soft);border-radius:8px;padding:10px 12px;margin-bottom:12px">
      <p style="font-size:11px;color:var(--signal);margin:0 0 2px;font-weight:600">Guardrails <span style="font-weight:400">from profile</span></p>
      <p style="font-size:12px;color:var(--signal);margin:0">${t.guardrailsApplied || "None set."}</p>
    </div>
    ${changesHtml}
    <p class="hint">${t.reviewerNotes || ""}</p>
    <div class="actions">
      <button id="cv-reject-btn" ${isDecided ? "disabled" : ""}>Reject</button>
      <button id="cv-approve-btn" class="primary" ${isDecided ? "disabled" : ""}>Approve &amp; download</button>
      ${t.status === "approved" ? `<a href="/api/cv-download/${currentUser}/${jobId}">Download final CV</a>` : ""}
    </div>
    <p class="hint">Status: ${t.status}</p>
  `;
  if (!isDecided) {
    $("cv-reject-btn").onclick = () => decideCv(jobId, "reject");
    $("cv-approve-btn").onclick = () => decideCv(jobId, "approve");
  }
}

async function decideCv(jobId, decision) {
  await fetch(`/api/cv-tailoring/${currentUser}/${jobId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision })
  });
  loadCvTailoring(jobId);
}

// --- Application queue ---
async function loadApplyQueue() {
  const res = await fetch(`/api/apply-queue/${currentUser}`);
  const queue = await res.json();
  const list = $("apply-list");
  if (!queue.length) {
    list.innerHTML = `<p class="hint">No jobs ready to apply yet. Approve a CV in the workspace first.</p>`;
    return;
  }
  list.innerHTML = queue.map(j => `
    <div class="field-group">
      <p style="font-weight:500;margin:0 0 4px">${j.title} \u2014 ${j.company}</p>
      <p class="hint" style="margin:0 0 8px">Form prep and submission happen outside this dashboard.</p>
      <span class="tag" style="background:var(--danger-soft);color:var(--danger)">Submit disabled here \u2014 always manual</span>
      <div class="actions">
        <a href="${j.url}" target="_blank">Open posting</a>
        <a href="/api/cv-download/${currentUser}/${j.id}">Download tailored CV</a>
        <button data-job="${j.id}" class="mark-applied-btn">I submitted this \u2014 mark applied</button>
      </div>
    </div>
  `).join("");
  document.querySelectorAll(".mark-applied-btn").forEach(btn => {
    btn.onclick = async () => {
      if (!confirm("Confirm you actually submitted this application. This just updates the tracker.")) return;
      await fetch(`/api/apply-queue/${currentUser}/${btn.dataset.job}/mark-applied`, { method: "POST" });
      loadApplyQueue();
    };
  });
}

// --- Inbox status ---
async function loadInboxStatus() {
  const res = await fetch(`/api/inbox-status?username=${currentUser}`);
  const s = await res.json();
  $("inbox-status").innerHTML = `
    <div class="row-field"><span><i class="ti ti-folder"></i> /inbox/linkedin</span><span class="hint mono">${s.linkedin} pending</span></div>
    <div class="row-field"><span><i class="ti ti-folder"></i> /inbox/naukri</span><span class="hint mono">${s.naukri} pending</span></div>
    <div class="row-field"><span><i class="ti ti-folder"></i> /inbox/indeed</span><span class="hint mono">${s.indeed} pending</span></div>
    <div class="row-field"><span><i class="ti ti-folder"></i> /cv-library</span><span class="hint mono">${s.cvLibrary} files</span></div>
  `;
}
