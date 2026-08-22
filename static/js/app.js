(function () {
  const textEl = document.getElementById("request-text");
  const triggerEl = document.getElementById("trigger-source");
  const runBtn = document.getElementById("run-btn");
  const statusEl = document.getElementById("demo-status");
  const rolePicker = document.getElementById("role-picker");

  const lines = document.querySelectorAll(".pline");

  const approvalPanel = document.getElementById("approval-panel");
  const approvalSummary = document.getElementById("approval-summary");
  const modifyRow = document.getElementById("modify-row");
  const modifyValue = document.getElementById("modify-value");
  const resultBanner = document.getElementById("result-banner");
  const resultText = document.getElementById("result-text");
  const permissionError = document.getElementById("permission-error");
  const whatifOutput = document.getElementById("whatif-output");

  const manualPanel = document.getElementById("manual-panel");
  const manualSummary = document.getElementById("manual-summary");

  let currentRecord = null;

  // -------------------------------------------------------------- helpers

  function currentRole() {
    return rolePicker.value;
  }

  async function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ------------------------------------------------------- example chips

  document.querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      textEl.value = chip.dataset.example;
      textEl.focus();
    });
  });

  // --------------------------------------------------------- voice input

  const voiceBtn = document.getElementById("voice-btn");
  const voiceStatus = document.getElementById("voice-status");
  const voiceLabel = voiceBtn ? voiceBtn.querySelector(".voice-label") : null;
  let recognition = null;
  let listening = false;

  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (voiceBtn) {
    if (!SpeechRecognitionAPI) {
      voiceBtn.disabled = true;
      voiceBtn.title = "Voice input isn't supported in this browser — try Chrome or Edge.";
      voiceStatus.textContent = "Voice input isn't supported in this browser — try Chrome or Edge.";
    } else {
      recognition = new SpeechRecognitionAPI();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        listening = true;
        voiceBtn.classList.add("listening");
        if (voiceLabel) voiceLabel.textContent = "Listening…";
        voiceStatus.textContent = "Listening — speak your request now.";
        voiceStatus.style.color = "var(--critical)";
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        textEl.value = transcript;
      };

      recognition.onerror = (event) => {
        voiceStatus.textContent =
          event.error === "not-allowed"
            ? "Microphone access was blocked — allow it in your browser's site settings and try again."
            : `Voice input error: ${event.error}`;
        voiceStatus.style.color = "var(--critical)";
      };

      recognition.onend = () => {
        listening = false;
        voiceBtn.classList.remove("listening");
        if (voiceLabel) voiceLabel.textContent = "Speak";
        if (textEl.value.trim()) {
          voiceStatus.textContent = "Got it — edit the text above if needed, then run the request.";
          voiceStatus.style.color = "var(--safe)";
        } else {
          voiceStatus.textContent = "";
        }
      };

      voiceBtn.addEventListener("click", () => {
        if (listening) {
          recognition.stop();
          return;
        }
        textEl.value = "";
        voiceStatus.style.color = "var(--critical)";
        try {
          recognition.start();
        } catch (err) {
          voiceStatus.textContent = "Couldn't start voice input — try clicking again.";
        }
      });
    }
  }

  // ------------------------------------------------------- pipeline strip

  function resetPipeline() {
    document.querySelectorAll(".pnode").forEach((n) => n.classList.remove("active", "waiting"));
    lines.forEach((l) => l.classList.remove("active", "done"));
  }

  function lightPipelineNode(name, mode) {
    const el = document.querySelector(`.pnode[data-node="${name}"]`);
    if (!el) return;
    el.classList.remove("waiting");
    el.classList.add(mode === "waiting" ? "waiting" : "active");
  }

  function lightPipelineLine(index) {
    const l = document.querySelector(`.pline[data-line="${index}"]`);
    if (!l) return;
    l.classList.add("active");
    setTimeout(() => l.classList.add("done"), 500);
  }

  // -------------------------------------------------- agent monitor + graph

  const AGENT_ROW_MAP = {
    intake: "intake",
    decision: "decision",
    risk: "risk",
    human: "human",
    action: "action",
    recovery: "recovery",
  };

  function resetAgentMonitor() {
    document.querySelectorAll(".agent-row").forEach((row) => {
      row.classList.remove("status-processing", "status-completed", "status-waiting", "status-skipped");
      row.querySelector(".agent-status").textContent = "Idle";
    });
    document.querySelectorAll(".gnode").forEach((n) => n.classList.remove("active", "waiting"));
    document.querySelectorAll(".gedge").forEach((e) => e.classList.remove("active"));
  }

  function setAgentStatus(agent, status, label) {
    const row = document.querySelector(`.agent-row[data-agent="${agent}"]`);
    if (row) {
      row.classList.remove("status-processing", "status-completed", "status-waiting", "status-skipped");
      row.classList.add(`status-${status}`);
      row.querySelector(".agent-status").textContent = label;
    }
    const gnode = document.querySelector(`.gnode[data-gnode="${agent}"]`);
    if (gnode) {
      gnode.classList.remove("active", "waiting");
      if (status === "processing" || status === "completed") gnode.classList.add("active");
      if (status === "waiting") gnode.classList.add("waiting");
    }
  }

  function lightEdge(name) {
    const e = document.querySelector(`.gedge[data-edge="${name}"]`);
    if (e) e.classList.add("active");
  }

  // ------------------------------------------------------ full run animation

  async function animateAutoRun(record) {
    resetPipeline();
    resetAgentMonitor();

    lightPipelineNode("trigger");
    lightPipelineLine(0);
    await sleep(180);

    setAgentStatus("intake", "processing", "Processing");
    lightPipelineNode("intake");
    await sleep(260);
    setAgentStatus("intake", "completed", "Completed");
    lightPipelineLine(1);

    setAgentStatus("decision", "processing", "Planning");
    lightPipelineNode("decision");
    lightEdge("intake-decision");
    await sleep(260);
    setAgentStatus("decision", "completed", "Completed");
    lightPipelineLine(2);

    setAgentStatus("risk", "processing", "Scoring");
    lightPipelineNode("risk");
    lightEdge("decision-risk");
    await sleep(260);
    setAgentStatus("risk", "completed", "Completed");
    lightPipelineLine(3);

    if (record.autonomy_mode === "AUTO") {
      setAgentStatus("human", "skipped", "Not needed");
      setAgentStatus("action", "processing", "Executing");
      lightPipelineNode("human");
      lightPipelineLine(4);
      await sleep(200);
      lightPipelineNode("action");
      lightEdge("risk-human");
      lightEdge("human-action");
      await sleep(280);
      renderRecoveryAgent(record.result);
      setAgentStatus("action", record.result && record.result.success ? "completed" : "waiting", record.result && record.result.success ? "Completed" : "Escalated");
      lightPipelineLine(5);
      await sleep(200);
      lightPipelineNode("log");
    } else {
      setAgentStatus("human", "waiting", "Awaiting decision");
      lightPipelineNode("human", "waiting");
      lightPipelineLine(4);
      lightEdge("risk-human");
    }
  }

  function renderRecoveryAgent(result) {
    if (!result) return;
    const attempts = result.attempts || [];
    if (attempts.length > 1) {
      lightEdge("action-recovery");
      setAgentStatus("recovery", result.escalated ? "waiting" : "completed", result.escalated ? "Escalated" : "Recovered");
    } else {
      setAgentStatus("recovery", "skipped", "Not needed");
    }
  }

  // ------------------------------------------------------------- rendering

  function renderUnderstanding(record) {
    const u = record.understanding;
    document.getElementById("u-intent").textContent = u.intent || "—";
    document.getElementById("u-category").textContent = u.category || "—";
    document.getElementById("u-department").textContent = u.department || "—";
    document.getElementById("u-priority").textContent = u.priority || "—";
    document.getElementById("u-why").textContent = u.why_priority || "";
  }

  function renderRisk(record) {
    const r = record.risk;
    document.getElementById("risk-score").textContent = r.score;
    document.getElementById("risk-band").textContent = r.band;
    document.getElementById("risk-mode").textContent = record.autonomy_mode;
    document.getElementById("risk-why").textContent = r.why;
    requestAnimationFrame(() => {
      document.getElementById("risk-bar-fill").style.width = r.score + "%";
    });
  }

  function showApproval(record) {
    approvalPanel.hidden = false;
    manualPanel.hidden = true;
    permissionError.hidden = true;
    whatifOutput.hidden = true;
    approvalSummary.textContent = `AI recommends: ${record.plan.summary}`;
    if (record.plan.action_type === "refund") {
      modifyRow.hidden = false;
      modifyValue.value = record.plan.primary_value;
    } else {
      modifyRow.hidden = true;
    }
  }

  function hideApproval() {
    approvalPanel.hidden = true;
  }

  function showManualPanel(record) {
    manualPanel.hidden = false;
    manualSummary.textContent = record.result ? record.result.summary : manualSummary.textContent;
  }

  function showResult(record) {
    resultBanner.hidden = false;
    resultText.textContent = record.result ? record.result.summary : "No action taken.";
  }

  // ------------------------------------------------------------- run button

  runBtn.addEventListener("click", async () => {
    const text = textEl.value.trim();
    if (!text) {
      statusEl.textContent = "Type or pick a request first.";
      return;
    }
    hideApproval();
    manualPanel.hidden = true;
    resultBanner.hidden = true;
    statusEl.textContent = "Sending to intake agent…";
    runBtn.disabled = true;

    const trigger = triggerEl.value;
    const endpoint = trigger === "webhook" ? "/api/webhook" : "/api/process";
    const headers = { "Content-Type": "application/json" };
    if (trigger === "webhook") {
      statusEl.textContent = "Note: the demo webhook call has no real secret, so it will show what an unauthenticated attempt looks like unless you configured WEBHOOK_SECRET server-side.";
    }

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({ text, trigger_source: trigger }),
      });
      const record = await resp.json();

      if (!resp.ok) {
        statusEl.textContent = record.error || "Request could not be processed.";
        runBtn.disabled = false;
        return;
      }

      if (record.duplicate) {
        statusEl.textContent = "Duplicate event detected — execution prevented.";
        runBtn.disabled = false;
        refreshLog();
        refreshDashboard();
        return;
      }

      currentRecord = record;
      renderUnderstanding(record);
      renderRisk(record);
      await animateAutoRun(record);

      if (record.autonomy_mode === "AUTO") {
        statusEl.textContent = "Risk within auto-execute range — action ran with no approval needed.";
        showResult(record);
      } else {
        statusEl.textContent = `Paused for human approval (${record.autonomy_mode}).`;
        showApproval(record);
      }
    } catch (err) {
      statusEl.textContent = "Something went wrong talking to the backend.";
      console.error(err);
    } finally {
      runBtn.disabled = false;
      refreshLog();
      refreshDashboard();
    }
  });

  // --------------------------------------------------------- what-if buttons

  async function runWhatIf(scenario) {
    if (!currentRecord) return;
    const resp = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: currentRecord.id, scenario }),
    });
    const data = await resp.json();
    if (!resp.ok) return;
    whatifOutput.hidden = false;
    whatifOutput.innerHTML =
      `<h4>${escapeHtml(data.headline)}</h4><ol>` +
      data.predicted_steps.map((s) => `<li>${escapeHtml(s)}</li>`).join("") +
      `</ol>`;
  }

  document.getElementById("whatif-approve").addEventListener("click", () => runWhatIf("approve"));
  document.getElementById("whatif-reject").addEventListener("click", () => runWhatIf("reject"));

  // ------------------------------------------------------------ approvals

  document.querySelectorAll(".approval-actions .btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!currentRecord) return;
      const decision = btn.dataset.decision;
      const body = { request_id: currentRecord.id, decision, role: currentRole() };
      if (decision === "modify") body.modified_value = Number(modifyValue.value);

      const resp = await fetch("/api/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const record = await resp.json();

      if (!resp.ok) {
        permissionError.hidden = false;
        permissionError.textContent = record.error || "That decision was not allowed.";
        return;
      }
      permissionError.hidden = true;
      currentRecord = record;

      setAgentStatus("human", "completed", `${decision[0].toUpperCase()}${decision.slice(1)}d`);
      lightPipelineNode("human");
      lightPipelineLine(4);
      lightEdge("human-action");
      await sleep(200);

      if (decision === "reject") {
        statusEl.textContent = "Rejected — no action taken, case flagged for manual follow-up.";
        hideApproval();
        setAgentStatus("action", "skipped", "Not needed");
        showResult(record);
      } else if (record.status === "ready_for_manual_execution") {
        statusEl.textContent = "Approved. This is a MANUAL-risk action — the AI will not execute it automatically.";
        hideApproval();
        setAgentStatus("action", "waiting", "Needs human");
        showManualPanel(record);
      } else {
        setAgentStatus("action", "processing", "Executing");
        lightPipelineNode("action");
        await sleep(280);
        renderRecoveryAgent(record.result);
        setAgentStatus("action", record.result.success ? "completed" : "waiting", record.result.success ? "Completed" : "Escalated");
        lightPipelineLine(5);
        await sleep(150);
        lightPipelineNode("log");
        statusEl.textContent = decision === "modify" ? "Approved with a modified value." : "Approved as recommended.";
        hideApproval();
        showResult(record);
      }
      refreshLog();
      refreshDashboard();
    });
  });

  document.getElementById("complete-manual-btn").addEventListener("click", async () => {
    if (!currentRecord) return;
    const resp = await fetch("/api/complete-manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: currentRecord.id }),
    });
    const record = await resp.json();
    if (!resp.ok) return;
    currentRecord = record;
    manualPanel.hidden = true;
    setAgentStatus("action", "completed", "Manually done");
    lightPipelineLine(5);
    lightPipelineNode("log");
    statusEl.textContent = "Manual execution confirmed by human.";
    resultText.textContent = "Marked as manually completed. Audit trail updated.";
    resultBanner.hidden = false;
    refreshLog();
    refreshDashboard();
  });

  // ---------------------------------------------------------------- scheduler

  document.getElementById("schedule-btn").addEventListener("click", async () => {
    const text = textEl.value.trim();
    const delay = Number(document.getElementById("schedule-delay").value) || 15;
    if (!text) {
      statusEl.textContent = "Type or pick a request first, then schedule it.";
      return;
    }
    const resp = await fetch("/api/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, delay_seconds: delay }),
    });
    const data = await resp.json();
    if (resp.ok) {
      statusEl.textContent = `Queued as a cron trigger — will run automatically in ${delay}s, even if you close this tab.`;
      refreshScheduleQueue();
    }
  });

  async function refreshScheduleQueue() {
    try {
      const resp = await fetch("/api/schedule/queue");
      const items = await resp.json();
      const el = document.getElementById("schedule-queue-list");
      if (!items.length) {
        el.innerHTML = "";
        return;
      }
      el.innerHTML = items
        .map((i) => {
          const secsLeft = Math.max(0, Math.round(i.run_at_epoch - Date.now() / 1000));
          const statusClass = i.status === "dispatched" ? "qs-dispatched" : "qs-queued";
          const statusLabel = i.status === "dispatched" ? "dispatched ✓" : `in ${secsLeft}s`;
          return `<div class="schedule-queue-item"><span>${escapeHtml(i.text.slice(0, 60))}${i.text.length > 60 ? "…" : ""}</span><span class="${statusClass}">${statusLabel}</span></div>`;
        })
        .join("");
    } catch (err) {
      console.error(err);
    }
  }

  // ------------------------------------------------------------- admin panel

  async function loadThresholds() {
    try {
      const resp = await fetch("/api/thresholds");
      const data = await resp.json();
      document.getElementById("threshold-auto").value = data.auto_max;
      document.getElementById("threshold-supervised").value = data.supervised_max;
    } catch (err) {
      console.error(err);
    }
  }

  document.getElementById("save-thresholds-btn").addEventListener("click", async () => {
    const auto_max = Number(document.getElementById("threshold-auto").value);
    const supervised_max = Number(document.getElementById("threshold-supervised").value);
    const statusP = document.getElementById("admin-status");
    const resp = await fetch("/api/thresholds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: currentRole(), auto_max, supervised_max }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      statusP.textContent = data.error;
      statusP.style.color = "var(--critical)";
    } else {
      statusP.textContent = `Saved. AUTO ≤ ${data.auto_max}, SUPERVISED ≤ ${data.supervised_max}.`;
      statusP.style.color = "var(--safe)";
    }
  });

  // ------------------------------------------------------------- run log

  async function refreshLog() {
    try {
      const resp = await fetch("/api/runlog");
      const events = await resp.json();
      const body = document.getElementById("log-body");
      if (!events.length) {
        body.innerHTML = '<tr class="log-empty"><td colspan="3">No events yet. Run a request above.</td></tr>';
        return;
      }
      body.innerHTML = events
        .map(
          (e) =>
            `<tr><td>${e.timestamp}</td><td>#${e.request_id}</td><td>${escapeHtml(e.message)}</td></tr>`
        )
        .join("");
    } catch (err) {
      console.error(err);
    }
  }

  // ------------------------------------------------------------- dashboard

  async function refreshDashboard() {
    try {
      const resp = await fetch("/api/dashboard");
      const m = await resp.json();
      document.getElementById("m-total").textContent = m.total_requests;
      document.getElementById("m-auto").textContent = m.auto_executed;
      document.getElementById("m-pending").textContent = m.pending_approval;
      document.getElementById("m-awaiting-manual").textContent = m.awaiting_manual_execution;
      document.getElementById("m-approved").textContent = m.human_approved;
      document.getElementById("m-modified").textContent = m.human_modified;
      document.getElementById("m-rejected").textContent = m.human_rejected;
      document.getElementById("m-approval-rate").textContent = m.approval_rate + "%";
      document.getElementById("m-override-rate").textContent = m.override_rate + "%";
      document.getElementById("m-avg-risk").textContent = m.avg_risk_score;
      document.getElementById("m-avg-decision").textContent = m.avg_decision_seconds + "s";
      document.getElementById("m-duplicates").textContent = m.duplicates_prevented;
      document.getElementById("m-recovered").textContent = m.recovered_actions;
      document.getElementById("m-escalated").textContent = m.escalated_actions;
    } catch (err) {
      console.error(err);
    }
  }

  // ------------------------------------------------------- integration badges

  async function loadIntegrationStatus() {
    try {
      const resp = await fetch("/api/status");
      const s = await resp.json();
      const el = document.getElementById("integration-strip");
      const badges = [
        ["Groq AI", s.groq_enabled],
        ["Webhook auth", s.webhook_enabled],
      ];
      el.innerHTML = badges
        .map(([label, on]) => `<span class="integration-badge ${on ? "on" : ""}">${on ? "●" : "○"} ${label}${on ? "" : " (off)"}</span>`)
        .join("");
    } catch (err) {
      console.error(err);
    }
  }

  // ------------------------------------------------------------------- init

  refreshLog();
  refreshDashboard();
  loadIntegrationStatus();
  loadThresholds();
  refreshScheduleQueue();
  setInterval(refreshScheduleQueue, 4000);
})();