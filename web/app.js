const byId = (id) => document.getElementById(id);
const state = { job: null, clips: [], pollTimer: null };

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function time(seconds) {
  const minutes = Math.floor(Number(seconds) / 60);
  const rest = Math.floor(Number(seconds) % 60);
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function setError(message) {
  const element = byId("form-error");
  element.textContent = message || "";
  element.hidden = !message;
}

function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

async function loadHistory() {
  const jobs = await request("/api/jobs");
  const list = byId("job-list");
  list.replaceChildren();
  for (const item of jobs) {
    const button = el("button", `job-item ${state.job?.id === item.id ? "active" : ""}`);
    button.type = "button";
    button.append(el("strong", "", item.instruction), el("small", "", `${item.status} · ${new Date(item.created_at).toLocaleString()}`));
    button.addEventListener("click", () => openJob(item.id));
    list.append(button);
  }
}

function renderTimeline(job) {
  state.clips = job.timeline.map((clip) => ({ ...clip }));
  const container = byId("timeline");
  container.replaceChildren();
  const assetNames = Object.fromEntries(job.assets.map((asset) => [asset.id, asset.name]));
  if (!state.clips.length) container.append(el("div", "timeline-empty", "Timeline is being prepared."));
  state.clips.forEach((clip, index) => {
    const row = el("div", "clip-row");
    row.append(el("span", "clip-index", String(index + 1).padStart(2, "0")));
    const info = el("div", "clip-info");
    info.append(el("strong", "", assetNames[clip.asset_id] || clip.asset_id), el("small", "", clip.reason || "Selected clip"));
    row.append(info);
    for (const key of ["start", "end"]) {
      const input = el("input");
      input.type = "number";
      input.min = "0";
      input.step = "0.01";
      input.value = Number(clip[key]).toFixed(2);
      input.title = `${key} time in seconds`;
      input.addEventListener("change", () => { state.clips[index][key] = Number(input.value); updateTotal(); });
      row.append(input);
    }
    const actions = el("div", "clip-actions");
    for (const [symbol, title, handler] of [
      ["↑", "Move up", () => swap(index, index - 1)],
      ["↓", "Move down", () => swap(index, index + 1)],
      ["×", "Remove clip", () => removeClip(index)],
    ]) {
      const button = el("button", "", symbol);
      button.type = "button";
      button.title = title;
      button.setAttribute("aria-label", title);
      button.addEventListener("click", handler);
      actions.append(button);
    }
    row.append(actions);
    container.append(row);
  });
  updateTotal();
  byId("save-timeline").hidden = !state.clips.length || !["complete", "needs_review"].includes(job.status);
}

function updateTotal() {
  const seconds = state.clips.reduce((sum, clip) => sum + Math.max(0, clip.end - clip.start), 0);
  byId("timeline-total").textContent = `${state.clips.length} clips · ${time(seconds)}`;
}

function swap(a, b) {
  if (b < 0 || b >= state.clips.length) return;
  [state.clips[a], state.clips[b]] = [state.clips[b], state.clips[a]];
  renderTimeline({ ...state.job, timeline: state.clips });
}

function removeClip(index) {
  if (state.clips.length <= 1) return;
  state.clips.splice(index, 1);
  renderTimeline({ ...state.job, timeline: state.clips });
}

function renderChecks(job) {
  const container = byId("checks");
  container.replaceChildren();
  const checks = job.report?.checks;
  if (!checks) {
    container.append(el("div", "timeline-empty", "Checks will appear after export."));
    return;
  }
  for (const [label, value, warning] of [
    ["Playable", checks.decodable ? "Passed" : "Failed", !checks.decodable],
    ["Duration", `${time(checks.duration)} ${checks.duration_ok ? "· passed" : "· review"}`, !checks.duration_ok],
    ["Aspect ratio", checks.aspect_ok ? "Passed" : "Review", !checks.aspect_ok],
    ["Audio stream", checks.has_audio ? "Present" : "Missing", !checks.has_audio],
    ["Subtitle cues", String(checks.subtitle_cues), !checks.subtitle_within_video],
    ["Timeline version", String(job.version), false],
  ]) {
    const row = el("div", `check-row ${warning ? "warn" : ""}`);
    row.append(el("span", "", label), el("span", "", value));
    container.append(row);
  }
  for (const issue of job.report.unresolved || []) container.append(el("div", "check-issue", issue));
}

function renderEvidence(job) {
  const container = byId("evidence");
  container.replaceChildren();
  byId("evidence-count").textContent = `${job.transcript.length} spans`;
  const selected = new Set(job.timeline.flatMap((clip) => clip.evidence_ids || []));
  for (const cue of job.transcript) {
    const item = el("div", "evidence-item");
    const asset = job.assets.find((source) => source.id === cue.asset_id);
    item.append(el("small", "", `${selected.has(cue.id) ? "SELECTED · " : ""}${asset?.name || cue.asset_id} · ${time(cue.start)}–${time(cue.end)}`), el("p", "", cue.text));
    container.append(item);
  }
  if (!job.transcript.length) container.append(el("div", "timeline-empty", "No spoken evidence found yet."));
}

function renderActivity(job) {
  const container = byId("activity");
  container.replaceChildren();
  for (const entry of [...job.events].reverse().slice(0, 15)) {
    const item = el("div", "activity-item");
    item.append(el("span", "", `${entry.message} · ${new Date(entry.at).toLocaleTimeString()}`));
    container.append(item);
  }
}

function renderJob(job) {
  state.job = job;
  byId("empty-state").hidden = true;
  byId("job-view").hidden = false;
  byId("job-title").textContent = job.instruction;
  const badge = byId("job-status");
  badge.className = `badge ${job.status}`;
  badge.textContent = job.status.replace("_", " ");
  const active = ["queued", "running"].includes(job.status);
  byId("progress").hidden = !active;
  byId("progress-text").textContent = job.phase.replace("_", " ");
  const progress = { queued: 8, transcribing: 25, planning: 45, rendering: 70, verifying: 90, replanning: 40 };
  byId("progress-bar").style.width = `${progress[job.phase] || 15}%`;
  byId("job-error").hidden = !job.error;
  byId("job-error").textContent = job.error || "";
  const ready = ["complete", "needs_review"].includes(job.status);
  byId("preview-video").parentElement.classList.toggle("portrait", job.options.aspect === "9:16");
  const video = byId("preview-video");
  if (ready) {
    const url = `/api/jobs/${job.id}/video?v=${job.version}`;
    if (video.dataset.url !== url) { video.src = url; video.dataset.url = url; video.load(); }
  }
  byId("video-placeholder").hidden = ready;
  byId("video-link").hidden = !ready;
  byId("subtitle-link").hidden = !ready;
  byId("timeline-link").hidden = !ready;
  byId("report-link").hidden = !ready;
  byId("video-link").href = `/api/jobs/${job.id}/video`;
  byId("subtitle-link").href = `/api/jobs/${job.id}/subtitles`;
  byId("subtitle-link").download = "captions.srt";
  byId("timeline-link").href = `/api/jobs/${job.id}/timeline.json`;
  byId("report-link").href = `/api/jobs/${job.id}/report.json`;
  byId("preview-meta").textContent = ready ? `${job.report.checks.width} × ${job.report.checks.height}` : "";
  renderTimeline(job);
  renderChecks(job);
  renderEvidence(job);
  renderActivity(job);
  byId("revise-button").disabled = !ready;
}

async function openJob(jobId) {
  clearTimeout(state.pollTimer);
  try {
    const job = await request(`/api/jobs/${jobId}`);
    renderJob(job);
    await loadHistory();
    if (["queued", "running"].includes(job.status)) state.pollTimer = setTimeout(() => openJob(jobId), 1100);
  } catch (error) { setError(error.message); }
}

byId("edit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");
  const button = event.submitter;
  button.disabled = true;
  try {
    const data = new FormData(event.currentTarget);
    const result = await request("/api/jobs", { method: "POST", body: data });
    await openJob(result.id);
  } catch (error) { setError(error.message); }
  finally { button.disabled = false; }
});

byId("demo-button").addEventListener("click", async () => {
  setError("");
  const button = byId("demo-button");
  button.disabled = true;
  try {
    const result = await request("/api/demo", { method: "POST" });
    await openJob(result.id);
  } catch (error) { setError(error.message); }
  finally { button.disabled = false; }
});

byId("save-timeline").addEventListener("click", async () => {
  setError("");
  try {
    const clips = state.clips.map(({ asset_id, start, end }) => ({ asset_id, start, end }));
    await request(`/api/jobs/${state.job.id}/timeline`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clips }),
    });
    await openJob(state.job.id);
  } catch (error) { setError(error.message); }
});

byId("revise-button").addEventListener("click", async () => {
  const instruction = byId("revision-text").value.trim();
  if (!instruction) return;
  setError("");
  try {
    await request(`/api/jobs/${state.job.id}/revise`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ instruction }),
    });
    byId("revision-text").value = "";
    await openJob(state.job.id);
  } catch (error) { setError(error.message); }
});

loadHistory().catch((error) => setError(error.message));
