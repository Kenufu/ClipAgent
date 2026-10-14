const byId = (id) => document.getElementById(id);
const state = { job: null, clips: [], original: "", jobs: [], pollTimer: null, activeTab: "evidence" };
const phases = ["Transcribe", "Plan", "Render", "Verify"];
const statusNames = { queued: "Queued", running: "Running", complete: "Complete", needs_review: "Needs review", failed: "Failed" };

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function el(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}

function icon(name) {
  const element = el("span", `icon icon-${name}`);
  element.setAttribute("aria-hidden", "true");
  return element;
}

function time(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
}

function setError(message, form = false) {
  const element = byId(form ? "form-error" : "workspace-error");
  element.textContent = message || "";
  element.hidden = !message;
}

function draftSignature(clips) {
  return JSON.stringify(clips.map(({ asset_id, start, end }) => ({ asset_id, start, end })));
}

function renderHistory() {
  const list = byId("job-list");
  const query = byId("job-search").value.trim().toLowerCase();
  const jobs = state.jobs.filter((job) => job.instruction.toLowerCase().includes(query));
  list.replaceChildren();
  byId("job-count").textContent = String(state.jobs.length);
  if (!jobs.length) {
    list.append(el("div", "rail-empty", query ? "No matching edits" : "No edits yet"));
    return;
  }
  for (const job of jobs) {
    const button = el("button", `job-item ${state.job?.id === job.id ? "active" : ""}`);
    button.type = "button";
    button.title = job.instruction;
    const dot = el("span", `job-dot ${job.status}`);
    const copy = el("span", "job-text");
    copy.append(el("strong", "", job.instruction), el("small", "", `${statusNames[job.status] || job.status} · ${new Date(job.created_at).toLocaleDateString()}`));
    button.append(dot, copy);
    button.addEventListener("click", () => openJob(job.id));
    list.append(button);
  }
}

async function loadHistory() {
  state.jobs = await request("/api/jobs");
  renderHistory();
}

function switchTab(name, focus = false) {
  state.activeTab = name;
  for (const tab of ["evidence", "checks", "activity"]) {
    const button = byId(`tab-${tab}`);
    const selected = tab === name;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
    byId(`panel-${tab}`).hidden = !selected;
  }
  if (focus) byId(`tab-${name}`).focus();
}

function seekToClip(index, sourceTime = null) {
  const video = byId("preview-video");
  if (!video.src || !state.clips[index]) return;
  const offset = state.clips.slice(0, index).reduce((sum, clip) => sum + clip.end - clip.start, 0);
  const clip = state.clips[index];
  const inside = sourceTime === null ? 0 : Math.max(0, Math.min(sourceTime - clip.start, clip.end - clip.start));
  video.currentTime = offset + inside;
  video.scrollIntoView({ behavior: "smooth", block: "nearest" });
  updatePlayback();
}

function updatePlayback() {
  const video = byId("preview-video");
  const position = video.currentTime || 0;
  let offset = 0;
  let active = -1;
  state.clips.forEach((clip, index) => {
    if (position >= offset && position < offset + clip.end - clip.start + 0.05) active = index;
    offset += clip.end - clip.start;
  });
  for (const segment of byId("timeline-track").querySelectorAll(".track-segment")) {
    segment.classList.toggle("current", Number(segment.dataset.index) === active);
  }
}

function renderTrack() {
  const track = byId("timeline-track");
  track.replaceChildren();
  if (!state.clips.length) {
    track.append(el("div", "timeline-empty", "The timeline is being prepared."));
    return;
  }
  const assetNames = Object.fromEntries(state.job.assets.map((asset) => [asset.id, asset.name]));
  state.clips.forEach((clip, index) => {
    const segment = el("button", "track-segment");
    segment.type = "button";
    segment.dataset.index = String(index);
    const duration = clip.end - clip.start;
    segment.style.flexGrow = String(Number.isFinite(duration) ? Math.max(0.5, duration) : 0.5);
    segment.style.flexBasis = "0";
    segment.disabled = !["complete", "needs_review"].includes(state.job.status);
    segment.title = `${assetNames[clip.asset_id] || clip.asset_id} · ${time(clip.start)}–${time(clip.end)} · Jump to clip`;
    segment.append(el("strong", "", String(index + 1).padStart(2, "0")), el("small", "", assetNames[clip.asset_id] || clip.asset_id));
    segment.addEventListener("click", () => seekToClip(index));
    track.append(segment);
  });
  updatePlayback();
}

function updateTotal() {
  const seconds = state.clips.reduce((sum, clip) => sum + Math.max(0, clip.end - clip.start), 0);
  byId("timeline-total").textContent = `${state.clips.length} clips · ${time(seconds)}`;
  const dirty = draftSignature(state.clips) !== state.original;
  const valid = state.clips.every((clip) => {
    const asset = state.job.assets.find((source) => source.id === clip.asset_id);
    return asset && Number.isFinite(clip.start) && Number.isFinite(clip.end) && clip.start >= 0 && clip.end > clip.start && clip.end <= asset.duration + 0.05;
  });
  const save = byId("save-timeline");
  save.hidden = !["complete", "needs_review"].includes(state.job.status) || !dirty;
  save.disabled = !valid;
}

function renderTimelineRows() {
  const container = byId("timeline");
  container.replaceChildren();
  if (!state.clips.length) {
    container.append(el("div", "timeline-empty", "Selected clips will appear here."));
    updateTotal();
    renderTrack();
    return;
  }
  const assets = Object.fromEntries(state.job.assets.map((asset) => [asset.id, asset]));
  state.clips.forEach((clip, index) => {
    const row = el("div", "clip-row");
    row.append(el("span", "clip-index", String(index + 1).padStart(2, "0")));
    const info = el("div", "clip-info");
    info.append(el("strong", "", assets[clip.asset_id]?.name || clip.asset_id), el("small", "", clip.reason || "Selected clip"));
    row.append(info);
    const times = el("div", "clip-times");
    for (const key of ["start", "end"]) {
      const label = el("label");
      label.append(el("span", "", key === "start" ? "IN / SEC" : "OUT / SEC"));
      const input = el("input");
      input.type = "number";
      input.min = "0";
      input.max = String(assets[clip.asset_id]?.duration || 600);
      input.step = "0.01";
      input.required = true;
      input.value = Number(clip[key]).toFixed(2);
      input.setAttribute("aria-label", `Clip ${index + 1} ${key} time in seconds`);
      input.addEventListener("input", () => {
        state.clips[index][key] = input.value === "" ? NaN : Number(input.value);
        updateTotal();
        renderTrack();
      });
      label.append(input);
      times.append(label);
    }
    row.append(times);
    const actions = el("div", "clip-actions");
    for (const [name, title, handler, disabled, danger] of [
      ["arrow-up", "Move clip up", () => swapClip(index, index - 1), index === 0, false],
      ["arrow-down", "Move clip down", () => swapClip(index, index + 1), index === state.clips.length - 1, false],
      ["trash-2", "Remove clip", () => removeClip(index), state.clips.length === 1, true],
    ]) {
      const button = el("button", `icon-button ${danger ? "danger" : ""}`);
      button.type = "button";
      button.title = title;
      button.setAttribute("aria-label", title);
      button.disabled = disabled;
      button.append(icon(name));
      button.addEventListener("click", handler);
      actions.append(button);
    }
    row.append(actions);
    container.append(row);
  });
  updateTotal();
  renderTrack();
}

function swapClip(a, b) {
  if (b < 0 || b >= state.clips.length) return;
  [state.clips[a], state.clips[b]] = [state.clips[b], state.clips[a]];
  renderTimelineRows();
}

function removeClip(index) {
  if (state.clips.length <= 1) return;
  state.clips.splice(index, 1);
  renderTimelineRows();
}

function checkRow(label, value, warning = false) {
  const row = el("div", `check-row ${warning ? "warn" : ""}`);
  row.append(icon(warning ? "triangle-alert" : "circle-check"), el("span", "", label), el("strong", "", value));
  return row;
}

function renderChecks(job) {
  const container = byId("checks");
  container.replaceChildren();
  const report = job.report;
  if (!report?.checks) {
    byId("checks-count").textContent = "Pending";
    container.append(el("div", "timeline-empty", "Checks appear after rendering."));
    return;
  }
  byId("checks-count").textContent = report.unresolved?.length ? `${report.unresolved.length} to review` : "All clear";
  if (report.topic_evidence?.length) {
    container.append(el("h3", "", "Required topics"));
    for (const topic of report.topic_evidence) container.append(checkRow(topic.topic, topic.verified ? "Found" : "Missing", !topic.verified));
  }
  const checks = report.checks;
  container.append(el("h3", "", "Output"));
  for (const [label, value, warning] of [
    ["Playable video", checks.decodable ? "Passed" : "Failed", !checks.decodable],
    ["Duration", `${time(checks.duration)} · ${checks.duration_ok ? "Passed" : "Review"}`, !checks.duration_ok],
    ["Aspect ratio", checks.aspect_ok ? "Passed" : "Review", !checks.aspect_ok],
    ["Audio stream", checks.has_audio ? "Present" : "Missing", !checks.has_audio],
    ["Subtitles", `${checks.subtitle_cues || 0} cues`, !checks.subtitle_within_video],
  ]) container.append(checkRow(label, value, warning));
  for (const issue of report.unresolved || []) container.append(el("div", "check-issue", issue));
}

function renderEvidence(job) {
  const container = byId("evidence");
  container.replaceChildren();
  byId("evidence-count").textContent = `${job.transcript.length} spans`;
  const names = Object.fromEntries(job.assets.map((asset) => [asset.id, asset.name]));
  for (const cue of job.transcript) {
    const clipIndex = job.timeline.findIndex((clip) => clip.asset_id === cue.asset_id && (clip.evidence_ids || []).includes(cue.id));
    const selected = clipIndex !== -1;
    const item = el(selected ? "button" : "div", `evidence-item ${selected ? "selected" : ""}`);
    if (selected) {
      item.type = "button";
      item.title = "Jump to this evidence in the edited video";
      item.addEventListener("click", () => seekToClip(clipIndex, cue.start));
    }
    const head = el("div", "evidence-item-head");
    head.append(el("span", "", `${names[cue.asset_id] || cue.asset_id} · ${time(cue.start)}–${time(cue.end)}`));
    if (selected) head.append(icon("play"));
    item.append(head, el("p", "", cue.text));
    container.append(item);
  }
  if (!job.transcript.length) container.append(el("div", "timeline-empty", "No spoken evidence found."));
}

function renderActivity(job) {
  const container = byId("activity");
  container.replaceChildren();
  byId("activity-count").textContent = `${job.events.length} events`;
  for (const entry of [...job.events].reverse()) {
    const item = el("div", "activity-item");
    const details = el("div");
    details.append(el("strong", "", entry.message), el("small", "", `${entry.phase.replaceAll("_", " ")} · ${new Date(entry.at).toLocaleString()}`));
    item.append(icon("clock-3"), details);
    container.append(item);
  }
}

function renderProgress(job) {
  const active = ["queued", "running"].includes(job.status);
  byId("progress").hidden = !active;
  if (!active) return;
  const stepIndex = { queued: -1, transcribing: 0, planning: 1, replanning: 1, rendering: 2, repairing: 2, verifying: 3 }[job.phase] ?? -1;
  const percentages = [9, 26, 48, 73, 91];
  byId("progress-bar").style.width = `${percentages[stepIndex + 1]}%`;
  byId("progress-text").textContent = job.phase.replaceAll("_", " ");
  byId("progress-detail").textContent = job.events.at(-1)?.message || "";
  const steps = byId("phase-steps");
  steps.replaceChildren();
  phases.forEach((phase, index) => steps.append(el("span", `phase-step ${index < stepIndex ? "done" : index === stepIndex ? "current" : ""}`, phase)));
}

function renderJob(job) {
  const changedJob = state.job?.id !== job.id;
  state.job = job;
  byId("empty-state").hidden = true;
  byId("job-view").hidden = false;
  byId("job-title").textContent = job.instruction;
  byId("job-short-id").textContent = `#${job.id.slice(0, 8).toUpperCase()}`;
  const badge = byId("job-status");
  badge.className = `status-badge ${job.status}`;
  badge.textContent = statusNames[job.status] || job.status;
  renderProgress(job);
  setError(job.error || "");
  const ready = ["complete", "needs_review"].includes(job.status);
  const video = byId("preview-video");
  video.parentElement.classList.toggle("portrait", job.options.aspect === "9:16");
  video.hidden = !ready;
  if (ready) {
    const url = `/api/jobs/${job.id}/video?v=${job.version}`;
    if (video.dataset.url !== url) {
      video.src = url;
      video.dataset.url = url;
      video.load();
    }
  } else if (video.dataset.url) {
    video.removeAttribute("src");
    video.dataset.url = "";
    video.load();
  }
  byId("video-placeholder").hidden = ready;
  for (const [id, artifact] of [["video-link", "video"], ["subtitle-link", "subtitles"], ["timeline-link", "timeline.json"], ["report-link", "report.json"]]) {
    const link = byId(id);
    link.hidden = !ready;
    link.href = `/api/jobs/${job.id}/${artifact}`;
  }
  byId("subtitle-link").download = "captions.srt";
  const checks = job.report?.checks;
  byId("preview-meta").textContent = ready && checks ? `${checks.width} × ${checks.height}` : "";
  byId("output-summary").textContent = ready && checks ? `${Math.round(checks.duration)}s output · v${job.version}` : `${job.assets.length} source${job.assets.length === 1 ? "" : "s"}`;
  state.clips = job.timeline.map((clip) => ({ ...clip }));
  state.original = draftSignature(state.clips);
  renderTimelineRows();
  renderChecks(job);
  renderEvidence(job);
  renderActivity(job);
  byId("revise-button").disabled = !ready;
  if (changedJob) switchTab(job.status === "needs_review" ? "checks" : "evidence");
}

async function openJob(jobId) {
  clearTimeout(state.pollTimer);
  try {
    const job = await request(`/api/jobs/${jobId}`);
    renderJob(job);
    localStorage.setItem("clipagent.currentJob", jobId);
    await loadHistory();
    if (["queued", "running"].includes(job.status)) state.pollTimer = setTimeout(() => openJob(jobId), 1200);
  } catch (error) {
    setError(error.message);
  }
}

function showCreateDialog() {
  setError("", true);
  byId("create-dialog").showModal();
  byId("files").focus();
}

for (const id of ["new-edit-button", "empty-new-edit"]) byId(id).addEventListener("click", showCreateDialog);
for (const id of ["close-dialog", "cancel-dialog"]) byId(id).addEventListener("click", () => byId("create-dialog").close());
byId("create-dialog").addEventListener("click", (event) => { if (event.target === byId("create-dialog")) byId("create-dialog").close(); });
byId("files").addEventListener("change", (event) => {
  const files = [...event.target.files];
  byId("file-summary").textContent = files.length ? files.map((file) => file.name).join(", ") : "Choose video files";
});
byId("job-search").addEventListener("input", renderHistory);
byId("preview-video").addEventListener("timeupdate", updatePlayback);

for (const tab of ["evidence", "checks", "activity"]) {
  const button = byId(`tab-${tab}`);
  button.addEventListener("click", () => switchTab(tab));
  button.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = ["evidence", "checks", "activity"];
    const current = tabs.indexOf(tab);
    const next = event.key === "Home" ? 0 : event.key === "End" ? 2 : (current + (event.key === "ArrowRight" ? 1 : 2)) % 3;
    switchTab(tabs[next], true);
  });
}

byId("edit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("", true);
  const files = byId("files").files;
  if (!files.length || files.length > 3) return setError("Choose 1–3 MP4 videos.", true);
  const button = event.submitter;
  button.disabled = true;
  try {
    const result = await request("/api/jobs", { method: "POST", body: new FormData(event.currentTarget) });
    byId("create-dialog").close();
    event.currentTarget.reset();
    byId("file-summary").textContent = "Choose video files";
    await openJob(result.id);
  } catch (error) {
    setError(error.message, true);
  } finally {
    button.disabled = false;
  }
});

async function runDemo(event) {
  const button = event.currentTarget;
  button.disabled = true;
  setError("");
  try {
    const result = await request("/api/demo", { method: "POST" });
    await openJob(result.id);
  } catch (error) {
    setError(error.message);
  } finally {
    button.disabled = false;
  }
}
for (const id of ["demo-button", "empty-demo"]) byId(id).addEventListener("click", runDemo);

byId("save-timeline").addEventListener("click", async (event) => {
  setError("");
  if (event.currentTarget.disabled) return;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const clips = state.clips.map(({ asset_id, start, end }) => ({ asset_id, start, end }));
    await request(`/api/jobs/${state.job.id}/timeline`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clips }) });
    await openJob(state.job.id);
  } catch (error) {
    setError(error.message);
    button.disabled = false;
  }
});

byId("revision-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = byId("revision-text");
  const instruction = input.value.trim();
  if (!instruction) return input.focus();
  setError("");
  const button = byId("revise-button");
  button.disabled = true;
  try {
    await request(`/api/jobs/${state.job.id}/revise`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ instruction }) });
    input.value = "";
    await openJob(state.job.id);
  } catch (error) {
    setError(error.message);
  } finally {
    button.disabled = !state.job || !["complete", "needs_review"].includes(state.job.status);
  }
});

async function init() {
  switchTab("evidence");
  try {
    await loadHistory();
    const saved = localStorage.getItem("clipagent.currentJob");
    const selected = state.jobs.find((job) => job.id === saved) || state.jobs[0];
    if (selected) await openJob(selected.id);
  } catch (error) {
    setError(error.message);
  }
}
init();
