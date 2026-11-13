const byId = (id) => document.getElementById(id);
const state = {
  job: null, clips: [], original: "", jobs: [], pollTimer: null, activeTab: "evidence",
  selectedAsset: null, monitorMode: "output", pixelsPerSecond: 30, playhead: 0,
};
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

function timelineDuration() {
  return state.clips.reduce((sum, clip) => {
    const duration = clip.end - clip.start;
    return sum + (Number.isFinite(duration) ? Math.max(0, duration) : 0);
  }, 0);
}

function switchMonitor(mode) {
  state.monitorMode = mode;
  const output = byId("preview-video");
  const source = byId("source-video");
  const sourceReady = Boolean(state.selectedAsset && source.dataset.assetId);
  output.hidden = mode !== "output" || !output.dataset.url;
  source.hidden = mode !== "source" || !sourceReady;
  byId("monitor-output").setAttribute("aria-selected", String(mode === "output"));
  byId("monitor-source").setAttribute("aria-selected", String(mode === "source"));
  byId("video-placeholder").hidden = mode === "output" ? Boolean(output.dataset.url) : sourceReady;
  byId("video-placeholder").textContent = mode === "output" ? "Preview appears when the edit is ready" : "Select source media to preview";
}

function selectSource(assetId, at = null) {
  const asset = state.job?.assets.find((item) => item.id === assetId);
  if (!asset) return;
  state.selectedAsset = assetId;
  const source = byId("source-video");
  const url = `/api/jobs/${state.job.id}/assets/${asset.id}/video`;
  if (source.dataset.url !== url) {
    source.src = url;
    source.dataset.url = url;
    source.dataset.assetId = asset.id;
    source.load();
  }
  if (at !== null) source.addEventListener("loadedmetadata", () => { source.currentTime = Math.min(at, source.duration || at); }, { once: true });
  for (const item of byId("source-list").querySelectorAll(".source-item")) item.classList.toggle("selected", item.dataset.assetId === assetId);
  byId("add-source-clip").disabled = !["complete", "needs_review"].includes(state.job.status);
  switchMonitor("source");
}

function renderSources(job) {
  const list = byId("source-list");
  list.replaceChildren();
  byId("source-count").textContent = `${job.assets.length} files`;
  for (const asset of job.assets) {
    const item = el("button", `source-item ${state.selectedAsset === asset.id ? "selected" : ""}`);
    item.type = "button";
    item.dataset.assetId = asset.id;
    item.title = `Preview ${asset.name}`;
    const image = el("img", "source-thumb");
    image.src = `/api/jobs/${job.id}/assets/${asset.id}/frame?at=${Math.min(1, asset.duration / 2)}`;
    image.alt = "";
    image.loading = "lazy";
    const copy = el("span", "source-copy");
    copy.append(el("strong", "", asset.name), el("small", "", `${time(asset.duration)} · ${asset.width}×${asset.height}`));
    item.append(image, copy);
    item.addEventListener("click", () => selectSource(asset.id));
    list.append(item);
  }
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
  switchMonitor("output");
  video.scrollIntoView({ behavior: "smooth", block: "nearest" });
  updatePlayback();
}

function updatePlayback() {
  const video = byId("preview-video");
  const position = video.currentTime || 0;
  state.playhead = position;
  let offset = 0;
  let active = -1;
  state.clips.forEach((clip, index) => {
    if (position >= offset && position < offset + clip.end - clip.start + 0.05) active = index;
    offset += clip.end - clip.start;
  });
  for (const segment of byId("timeline-track").querySelectorAll(".track-segment")) {
    segment.classList.toggle("current", Number(segment.dataset.index) === active);
  }
  const total = timelineDuration();
  byId("timeline-playhead").style.left = `${32 + Math.min(position, total) * state.pixelsPerSecond}px`;
  byId("playhead-time").textContent = `${time(position)} / ${time(total)}`;
}

function renderTrack() {
  const track = byId("timeline-track");
  track.replaceChildren();
  const ruler = byId("timeline-ruler");
  ruler.replaceChildren();
  const total = Math.max(1, timelineDuration());
  const scrollerWidth = Math.max(320, byId("timeline-scroller").clientWidth - 34);
  const trackWidth = Math.max(scrollerWidth, total * state.pixelsPerSecond);
  byId("timeline-content").style.width = `${trackWidth + 32}px`;
  const tickStep = state.pixelsPerSecond >= 40 ? 1 : state.pixelsPerSecond >= 25 ? 2 : 5;
  for (let second = 0; second <= Math.ceil(trackWidth / state.pixelsPerSecond); second += tickStep) {
    const tick = el("span", `ruler-tick ${second % (tickStep * 5) === 0 ? "major" : ""}`);
    tick.style.left = `${32 + second * state.pixelsPerSecond}px`;
    if (tick.classList.contains("major")) tick.append(el("span", "", time(second)));
    ruler.append(tick);
  }
  if (!state.clips.length) {
    track.append(el("div", "timeline-empty", "The timeline is being prepared."));
    updatePlayback();
    return;
  }
  const assets = Object.fromEntries(state.job.assets.map((asset) => [asset.id, asset]));
  let offset = 0;
  state.clips.forEach((clip, index) => {
    const segment = el("button", "track-segment");
    segment.type = "button";
    segment.dataset.index = String(index);
    const duration = clip.end - clip.start;
    segment.style.left = `${offset * state.pixelsPerSecond}px`;
    segment.style.width = `${Math.max(36, (Number.isFinite(duration) ? duration : 0.5) * state.pixelsPerSecond)}px`;
    segment.disabled = !["complete", "needs_review"].includes(state.job.status);
    segment.draggable = !segment.disabled;
    const asset = assets[clip.asset_id];
    segment.title = `${asset?.name || clip.asset_id} · ${time(clip.start)}–${time(clip.end)} · Jump to clip`;
    const media = el("span", "segment-media");
    for (const ratio of [0.08, 0.5, 0.92]) {
      const image = el("img");
      image.src = `/api/jobs/${state.job.id}/assets/${clip.asset_id}/frame?at=${Math.max(0, clip.start + duration * ratio)}`;
      image.alt = "";
      image.loading = "lazy";
      media.append(image);
    }
    const overlay = el("span", "segment-overlay");
    overlay.append(el("strong", "", `${String(index + 1).padStart(2, "0")}  ${asset?.name || clip.asset_id}`), el("small", "", `${clip.start.toFixed(2)}–${clip.end.toFixed(2)}`));
    const startHandle = el("span", "trim-handle start");
    const endHandle = el("span", "trim-handle end");
    startHandle.title = "Trim clip start";
    endHandle.title = "Trim clip end";
    startHandle.addEventListener("pointerdown", (event) => beginTrim(event, index, "start"));
    endHandle.addEventListener("pointerdown", (event) => beginTrim(event, index, "end"));
    segment.append(media, overlay, startHandle, endHandle);
    segment.addEventListener("click", (event) => { if (!event.target.closest(".trim-handle")) seekToClip(index); });
    segment.addEventListener("dragstart", (event) => event.dataTransfer.setData("text/plain", String(index)));
    segment.addEventListener("dragover", (event) => event.preventDefault());
    segment.addEventListener("drop", (event) => {
      event.preventDefault();
      const from = Number(event.dataTransfer.getData("text/plain"));
      if (Number.isInteger(from) && from !== index) moveClip(from, index);
    });
    track.append(segment);
    offset += Number.isFinite(duration) ? Math.max(0, duration) : 0;
  });
  updatePlayback();
}

function beginTrim(event, index, key) {
  if (!state.clips[index]) return;
  event.preventDefault();
  event.stopPropagation();
  const originX = event.clientX;
  const initial = state.clips[index][key];
  const asset = state.job.assets.find((item) => item.id === state.clips[index].asset_id);
  const move = (pointerEvent) => {
    const delta = (pointerEvent.clientX - originX) / state.pixelsPerSecond;
    const clip = state.clips[index];
    clip[key] = key === "start"
      ? Math.max(0, Math.min(clip.end - 0.1, initial + delta))
      : Math.min(asset.duration, Math.max(clip.start + 0.1, initial + delta));
    renderTrack();
    updateTotal();
  };
  const finish = () => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", finish);
    renderTimelineRows();
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", finish, { once: true });
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
  byId("draft-state").textContent = dirty ? (valid ? "Unsaved timeline draft" : "Fix invalid clip bounds") : "Rendered timeline";
  byId("split-clip").disabled = !valid || !state.clips.length || !["complete", "needs_review"].includes(state.job.status);
  updatePlayback();
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

function moveClip(from, to) {
  if (from < 0 || from >= state.clips.length || to < 0 || to >= state.clips.length) return;
  const [clip] = state.clips.splice(from, 1);
  state.clips.splice(to, 0, clip);
  renderTimelineRows();
}

function removeClip(index) {
  if (state.clips.length <= 1) return;
  state.clips.splice(index, 1);
  renderTimelineRows();
}

function splitAtPlayhead() {
  let offset = 0;
  for (let index = 0; index < state.clips.length; index += 1) {
    const clip = state.clips[index];
    const duration = clip.end - clip.start;
    if (state.playhead > offset + 0.1 && state.playhead < offset + duration - 0.1) {
      const sourceCut = clip.start + state.playhead - offset;
      state.clips.splice(index, 1,
        { ...clip, end: sourceCut, reason: "Manual split" },
        { ...clip, start: sourceCut, reason: "Manual split" });
      renderTimelineRows();
      return;
    }
    offset += duration;
  }
  setError("Move the playhead inside a clip before splitting.");
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
  for (const entry of job.events) {
    const item = el("div", "activity-item");
    const timestamp = el("time", "", new Date(entry.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    const details = el("div");
    details.append(el("strong", "", entry.phase.replaceAll("_", " ")), el("span", "", entry.message));
    item.append(timestamp, details);
    container.append(item);
  }
  container.scrollTop = container.scrollHeight;
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
  if (changedJob) state.selectedAsset = job.assets[0]?.id || null;
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
  renderSources(job);
  if (changedJob && state.selectedAsset) {
    const source = byId("source-video");
    const sourceUrl = `/api/jobs/${job.id}/assets/${state.selectedAsset}/video`;
    source.src = sourceUrl;
    source.dataset.url = sourceUrl;
    source.dataset.assetId = state.selectedAsset;
    source.load();
  }
  switchMonitor(state.monitorMode === "source" && state.selectedAsset ? "source" : "output");
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
  byId("add-source-clip").disabled = !ready || !state.selectedAsset;
  if (changedJob) switchTab(["queued", "running"].includes(job.status) ? "activity" : job.status === "needs_review" ? "checks" : "evidence");
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
byId("monitor-output").addEventListener("click", () => switchMonitor("output"));
byId("monitor-source").addEventListener("click", () => switchMonitor("source"));
byId("timeline-zoom").addEventListener("input", (event) => {
  state.pixelsPerSecond = Number(event.currentTarget.value);
  renderTrack();
});
byId("timeline-ruler").addEventListener("click", (event) => {
  const video = byId("preview-video");
  if (!video.dataset.url) return;
  const bounds = byId("timeline-content").getBoundingClientRect();
  const next = Math.max(0, Math.min(timelineDuration(), (event.clientX - bounds.left - 32) / state.pixelsPerSecond));
  video.currentTime = next;
  switchMonitor("output");
  updatePlayback();
});
byId("split-clip").addEventListener("click", splitAtPlayhead);
byId("add-source-clip").addEventListener("click", () => {
  const asset = state.job?.assets.find((item) => item.id === state.selectedAsset);
  if (!asset) return;
  const source = byId("source-video");
  const start = Math.min(Math.max(0, source.currentTime || 0), Math.max(0, asset.duration - 0.1));
  const end = Math.min(asset.duration, start + Math.min(5, asset.duration));
  if (end - start < 0.1) return setError("The selected source position is too close to the end.");
  state.clips.push({ asset_id: asset.id, start, end, evidence_ids: [], reason: "Manual source insert", required: false, score: 0 });
  renderTimelineRows();
});

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
