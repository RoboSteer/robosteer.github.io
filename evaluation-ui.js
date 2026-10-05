(() => {
  "use strict";
  const config = window.ROBOOSTEER_EVALUATION_CONFIG;
  const service = window.RoboSteerEvaluationService;
  const byId = id => document.getElementById(id);
  if (!config || !service || !byId("evaluation")) return;

  const groups = {
    csv: { values: ["speed", "amplitude", "direction", "trajectory", "body_restrain"], label: "CSV" },
    vlm: { values: ["order", "times"], label: "video" }
  };
  const csvSlots = Object.freeze({
    jointPos: { id: "joint-pos", expectedName: "joint_pos.csv" },
    bodyPos: { id: "body-pos", expectedName: "body_pos.csv" },
    bodyQuat: { id: "body-quat", expectedName: "body_quat.csv" }
  });
  const emptyCsvFiles = () => Object.fromEntries(Object.keys(csvSlots).map(slot => [slot, null]));
  const state = {
    csv: { files: emptyCsvFiles(), busy: false, constraint: "" },
    vlm: { file: null, busy: false, constraint: "" }
  };
  let activeType = "csv";
  const tab = type => byId(type === "csv" ? "tab-csv" : "tab-vlm");
  const panel = type => byId(type === "csv" ? "panel-csv" : "panel-vlm");
  const form = type => byId(`${type}-evaluation-form`);
  const resultBox = type => byId(`${type}-result-box`);

  function idleMessage(type) {
    return type === "csv"
      ? "Choose a constraint, enter a Task ID, and upload all three CSV files."
      : "Choose Order or Times, enter a Task ID, upload video, and provide your VLM credentials.";
  }

  function status(type, name, message) {
    const box = resultBox(type);
    box.dataset.state = name;
    box.replaceChildren();
    const content = document.createElement("div");
    content.className = "result-placeholder";
    const heading = document.createElement("h4");
    heading.textContent = name === "idle" ? "Evaluation Output" : name === "file-selected" ? "Files selected" : name === "validating" ? "Checking input" : name === "demo-loading" ? "Loading example…" : name === "evaluating" ? "Evaluating…" : name === "invalid-input" ? "Check your input" : "Evaluation unavailable";
    const text = document.createElement("p");
    text.textContent = message;
    content.append(heading, text);
    box.append(content);
  }

  function showResult(type, response) {
    const box = resultBox(type);
    const result = response.result;
    box.dataset.state = "success";
    box.replaceChildren();
    const wrap = document.createElement("div");
    wrap.className = "result-container";
    const header = document.createElement("div");
    header.className = "result-header";
    const title = document.createElement("strong");
    title.textContent = "Result";
    const context = document.createElement("span");
    context.className = "result-timestamp";
    context.textContent = `${response.constraint.replaceAll("_", " ")} · ${response.taskId}`;
    header.append(title, context);
    wrap.append(header);

    if (typeof result.satisfied === "boolean") {
      const verdict = document.createElement("div");
      verdict.className = `result-status-banner ${result.satisfied ? "status-pass" : "status-fail"}`;
      verdict.textContent = result.satisfied ? "✓ Constraint satisfied" : "✗ Constraint not satisfied";
      wrap.append(verdict);
    }
    if (result.score != null) {
      const score = document.createElement("div");
      score.className = "result-score";
      const label = document.createElement("span");
      label.textContent = "Score";
      const value = document.createElement("strong");
      value.textContent = String(result.score);
      score.append(label, value);
      wrap.append(score);
    }
    if (result.message) {
      const message = document.createElement("p");
      message.className = "result-explanation";
      message.textContent = result.message;
      wrap.append(message);
    }
    if (wrap.children.length === 1) {
      const note = document.createElement("p");
      note.textContent = "Evaluation completed. No result fields were returned.";
      wrap.append(note);
    }
    box.append(wrap);
  }

  function setActive(type) {
    activeType = type;
    for (const other of ["csv", "vlm"]) {
      const active = other === type;
      tab(other).classList.toggle("active", active);
      tab(other).setAttribute("aria-selected", String(active));
      panel(other).hidden = !active;
      panel(other).classList.toggle("active", active);
    }
    updateDemoButton(type);
  }

  function syncConstraintButtons(selected) {
    byId("eval-constraint-picker").querySelectorAll("button").forEach(button => {
      button.setAttribute("aria-pressed", String(button.dataset.constraint === selected));
    });
  }

  function csvDemoAvailable(demo) {
    const urls = demo?.csvAssetUrls;
    return Boolean(demo?.taskId?.trim() && urls && Object.keys(csvSlots).every(slot => urls[slot]?.trim()));
  }

  function videoDemoAvailable(demo) {
    return Boolean(demo?.taskId?.trim() && demo?.videoAssetUrl?.trim());
  }

  function updateDemoButton(type) {
    const constraint = byId(`${type}-constraint-select`).value;
    const demo = config.demos?.[constraint];
    const available = type === "csv" ? csvDemoAvailable(demo) : videoDemoAvailable(demo);
    byId(`${type}-demo-btn`).disabled = state[type].busy || !available;
    byId(`${type}-demo-note`).textContent = !constraint
      ? "Choose a constraint to check example availability."
      : available
        ? "Use a complete website example with its benchmark Task ID."
        : type === "csv"
          ? "No complete three-file example is configured yet. You can upload your own output."
          : "Example not configured yet. You can upload your own output.";
  }

  const configFileType = type => config.fileTypes[type === "csv" ? "csv" : "video"];
  function validFile(type, file) {
    if (!file) return "Choose a file.";
    if (file.size === 0) return "Choose a nonempty file.";
    const settings = configFileType(type);
    const dot = file.name.lastIndexOf(".");
    const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
    if (!settings.extensions.includes(extension)) return `Choose a ${settings.extensions.join(" or ")} file.`;
    if (file.type && file.type !== "application/octet-stream" && !settings.mimeTypes.includes(file.type)) return "This file type is not supported.";
    if (config.maxFileBytes != null && file.size > config.maxFileBytes) return "This file exceeds the configured upload size limit.";
    return "";
  }

  function formatFile(file) {
    return `${file.name} (${(file.size / 1048576).toFixed(2)} MB)`;
  }

  function selectedCsvCount() {
    return Object.values(state.csv.files).filter(Boolean).length;
  }

  function updateCsvSlot(slot) {
    const spec = csvSlots[slot];
    const file = state.csv.files[slot];
    const prefix = `csv-${spec.id}`;
    byId(`${prefix}-file-name`).textContent = file ? formatFile(file) : `Click or drop ${spec.expectedName} here`;
    byId(`${prefix}-dropzone`).classList.toggle("has-file", Boolean(file));
    byId(`${prefix}-file-actions`).hidden = !file;
    const note = byId(`${prefix}-file-note`);
    const mismatch = file && file.name.toLowerCase() !== spec.expectedName;
    note.classList.toggle("warning", Boolean(mismatch));
    note.textContent = mismatch
      ? `Selected “${file.name}” for the ${spec.expectedName} slot. This slot determines its meaning; confirm that the contents match.`
      : "The upload slot determines this file's meaning.";
  }

  function setCsvFile(slot, file, { silent = false } = {}) {
    const spec = csvSlots[slot];
    const error = file ? validFile("csv", file) : "";
    if (error) {
      state.csv.files[slot] = null;
      byId(`csv-${spec.id}-file-input`).value = "";
      updateCsvSlot(slot);
      if (!silent) status("csv", "invalid-input", `${spec.expectedName}: ${error}`);
      return false;
    }
    state.csv.files[slot] = file || null;
    updateCsvSlot(slot);
    if (!silent) {
      const count = selectedCsvCount();
      status("csv", count ? "file-selected" : "idle", count ? `${count} of 3 required CSV files selected.` : idleMessage("csv"));
    }
    return true;
  }

  function setVideoFile(file, { silent = false } = {}) {
    const error = file ? validFile("vlm", file) : "";
    if (error) {
      state.vlm.file = null;
      byId("vlm-file-input").value = "";
      byId("vlm-file-name").textContent = "Click or drop a video file here";
      byId("vlm-dropzone").classList.remove("has-file");
      byId("vlm-file-actions").hidden = true;
      if (!silent) status("vlm", "invalid-input", error);
      return false;
    }
    state.vlm.file = file || null;
    byId("vlm-file-name").textContent = file ? formatFile(file) : "Click or drop a video file here";
    byId("vlm-dropzone").classList.toggle("has-file", Boolean(file));
    byId("vlm-file-actions").hidden = !file;
    if (!silent) status("vlm", file ? "file-selected" : "idle", file ? `${file.name} is ready. Enter the remaining details and evaluate.` : idleMessage("vlm"));
    return true;
  }

  function clearUploads(type) {
    if (type === "csv") {
      for (const [slot, spec] of Object.entries(csvSlots)) {
        byId(`csv-${spec.id}-file-input`).value = "";
        state.csv.files[slot] = null;
        updateCsvSlot(slot);
      }
    } else {
      byId("vlm-file-input").value = "";
      setVideoFile(null, { silent: true });
    }
  }

  function clearInput(id) {
    const input = byId(id);
    input.value = "";
    input.defaultValue = "";
  }

  function clearVlmPrivateFields() {
    clearInput("vlm-api-key");
    clearInput("vlm-model-name");
    clearInput("vlm-base-url");
  }

  function resetType(type, { preserveConstraint = "", announce = true } = {}) {
    form(type).reset();
    clearInput(`${type}-task-id`);
    clearUploads(type);
    if (type === "vlm") {
      clearVlmPrivateFields();
      byId("vlm-provider-select").value = "";
    }
    byId(`${type}-constraint-select`).value = preserveConstraint;
    state[type].constraint = preserveConstraint;
    if (announce) status(type, "idle", idleMessage(type));
    updateDemoButton(type);
  }

  function clearForConstraint(type, value) {
    resetType(type, { preserveConstraint: value });
    byId(`${type}-task-id`).value = "";
    syncConstraintButtons(value);
  }

  function selectConstraint(value) {
    const type = groups.csv.values.includes(value) ? "csv" : "vlm";
    if (activeType !== type) {
      resetType(activeType, { announce: false });
      resetType(type, { announce: false });
      setActive(type);
    }
    if (state[type].constraint !== value) clearForConstraint(type, value);
    else syncConstraintButtons(value);
    updateProviderRequirements();
  }

  function clearStaleResult(type) {
    if (["success", "backend-error", "invalid-input"].includes(resultBox(type).dataset.state)) {
      const hasFile = type === "csv" ? selectedCsvCount() > 0 : Boolean(state.vlm.file);
      status(type, hasFile ? "file-selected" : "idle", hasFile ? "Files selected. Review the details and evaluate again." : idleMessage(type));
    }
  }

  function setupCsvSlot(slot) {
    const spec = csvSlots[slot];
    const prefix = `csv-${spec.id}`;
    const input = byId(`${prefix}-file-input`);
    const zone = byId(`${prefix}-dropzone`);
    input.accept = configFileType("csv").extensions.join(",");
    input.addEventListener("change", () => { if (!state.csv.busy && input.files[0]) setCsvFile(slot, input.files[0]); });
    zone.addEventListener("keydown", event => {
      if ((event.key === "Enter" || event.key === " ") && !state.csv.busy) { event.preventDefault(); input.click(); }
    });
    zone.addEventListener("dragover", event => { event.preventDefault(); if (!state.csv.busy) zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", event => {
      event.preventDefault();
      zone.classList.remove("drag-over");
      if (!state.csv.busy && event.dataTransfer.files[0]) setCsvFile(slot, event.dataTransfer.files[0]);
    });
    byId(`${prefix}-replace`).addEventListener("click", () => { if (!state.csv.busy) { input.value = ""; input.click(); } });
    byId(`${prefix}-remove`).addEventListener("click", () => { input.value = ""; setCsvFile(slot, null); });
  }

  function setupVideoFile() {
    const input = byId("vlm-file-input");
    const zone = byId("vlm-dropzone");
    input.accept = configFileType("vlm").extensions.join(",");
    input.addEventListener("change", () => { if (!state.vlm.busy && input.files[0]) setVideoFile(input.files[0]); });
    zone.addEventListener("keydown", event => {
      if ((event.key === "Enter" || event.key === " ") && !state.vlm.busy) { event.preventDefault(); input.click(); }
    });
    zone.addEventListener("dragover", event => { event.preventDefault(); if (!state.vlm.busy) zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", event => {
      event.preventDefault();
      zone.classList.remove("drag-over");
      if (!state.vlm.busy && event.dataTransfer.files[0]) setVideoFile(event.dataTransfer.files[0]);
    });
    byId("vlm-replace").addEventListener("click", () => { if (!state.vlm.busy) { input.value = ""; input.click(); } });
    byId("vlm-remove").addEventListener("click", () => { input.value = ""; setVideoFile(null); });
  }

  function setBusy(type, busy, label = "Evaluating…") {
    state[type].busy = busy;
    form(type).querySelectorAll("input, select, button").forEach(control => { control.disabled = busy; });
    byId("eval-constraint-picker").querySelectorAll("button").forEach(control => { control.disabled = busy; });
    for (const item of ["csv", "vlm"]) tab(item).disabled = busy;
    byId(`btn-eval-${type}`).textContent = busy ? label : "Evaluate";
    resultBox(type).setAttribute("aria-busy", String(busy));
    if (!busy) updateDemoButton(type);
  }

  async function prepareDemo(type) {
    if (state[type].busy) return;
    const constraint = byId(`${type}-constraint-select`).value;
    resetType(type, { preserveConstraint: constraint, announce: false });
    setBusy(type, true, "Loading example…");
    status(type, "demo-loading", "Loading the website example…");
    try {
      const demo = await service.loadDemo(constraint);
      byId(`${type}-task-id`).value = demo.taskId;
      if (type === "csv") {
        for (const slot of Object.keys(csvSlots)) {
          const error = validFile("csv", demo.files?.[slot]);
          if (error) throw new service.EvaluationError("INVALID_INPUT", `${csvSlots[slot].expectedName}: ${error}`);
          setCsvFile(slot, demo.files[slot], { silent: true });
        }
      } else {
        const error = validFile("vlm", demo.file);
        if (error) throw new service.EvaluationError("INVALID_INPUT", error);
        setVideoFile(demo.file, { silent: true });
      }
      status(type, "file-selected", "Example loaded. Click Evaluate to run the real backend evaluation.");
    } catch (caught) {
      clearUploads(type);
      byId(`${type}-task-id`).value = "";
      if (type === "vlm") byId("vlm-api-key").value = "";
      status(type, "backend-error", caught instanceof service.EvaluationError ? caught.message : "The example asset could not be loaded.");
    } finally {
      setBusy(type, false);
    }
  }

  function validateCsvFiles() {
    const missing = Object.entries(csvSlots).filter(([slot]) => !state.csv.files[slot]).map(([, spec]) => spec.expectedName);
    if (missing.length) return `Choose the missing file${missing.length > 1 ? "s" : ""}: ${missing.join(", ")}.`;
    for (const [slot, spec] of Object.entries(csvSlots)) {
      const error = validFile("csv", state.csv.files[slot]);
      if (error) return `${spec.expectedName}: ${error}`;
    }
    return "";
  }

  function updateProviderRequirements() {
    const provider = byId("vlm-provider-select").value;
    const selected = config.providers.find(item => item.id === provider);
    const baseInput = byId("vlm-base-url");
    baseInput.required = Boolean(selected?.requiresBaseUrl);
    baseInput.setAttribute("aria-required", String(Boolean(selected?.requiresBaseUrl)));
  }

  async function evaluate(type) {
    if (state[type].busy) return;
    status(type, "validating", "Checking your input…");
    const constraint = byId(`${type}-constraint-select`).value;
    const taskId = byId(`${type}-task-id`).value.trim();
    const provider = type === "vlm" ? byId("vlm-provider-select").value : "";
    const modelName = type === "vlm" ? byId("vlm-model-name").value.trim() : "";
    const baseInput = type === "vlm" ? byId("vlm-base-url") : null;
    const keyInput = type === "vlm" ? byId("vlm-api-key") : null;
    const apiKey = keyInput?.value || "";
    let baseUrl = baseInput?.value || "";
    let error = !constraint ? "Choose a constraint." : !taskId ? "Enter a Task ID." : "";

    if (!error && type === "csv") error = validateCsvFiles();
    if (!error && type === "vlm" && !state.vlm.file) error = "Choose a video file.";
    if (!error && type === "vlm") error = validFile("vlm", state.vlm.file);
    if (!error && type === "vlm" && !provider) error = "Choose a VLM provider.";
    if (!error && type === "vlm" && !modelName) error = "Enter a Model Name.";
    if (!error && type === "vlm") {
      try { baseUrl = service.normalizeBaseUrl(baseUrl); }
      catch (caught) { error = caught instanceof service.EvaluationError ? caught.message : "Enter a valid Base URL."; }
    }
    const providerConfig = config.providers.find(item => item.id === provider);
    if (!error && type === "vlm" && providerConfig?.requiresBaseUrl && !baseUrl) error = "Enter a Base URL for the custom provider.";
    if (!error && type === "vlm" && !apiKey.trim()) error = "Enter an API Key.";
    if (error) {
      if (keyInput) keyInput.value = "";
      status(type, "invalid-input", error);
      return;
    }
    if (baseInput) baseInput.value = baseUrl;

    setBusy(type, true);
    status(type, "evaluating", "Your sample is being evaluated…");
    try {
      const fields = type === "csv"
        ? { taskId, constraint, files: { ...state.csv.files } }
        : { taskId, constraint, file: state.vlm.file, provider, apiKey, baseUrl, modelName };
      const response = await (type === "csv" ? service.evaluateCsv(fields) : service.evaluateVideo(fields));
      showResult(type, response);
    } catch (caught) {
      clearUploads(type);
      status(type, "backend-error", caught instanceof service.EvaluationError ? caught.message : "Evaluation failed. Please try again.");
    } finally {
      if (keyInput) keyInput.value = "";
      setBusy(type, false);
    }
  }

  for (const [slot] of Object.entries(csvSlots)) setupCsvSlot(slot);
  setupVideoFile();

  for (const type of ["csv", "vlm"]) {
    form(type).addEventListener("submit", event => { event.preventDefault(); evaluate(type); });
    byId(`btn-reset-${type}`).addEventListener("click", () => {
      resetType(type);
      syncConstraintButtons("");
      updateProviderRequirements();
    });
    byId(`${type}-constraint-select`).addEventListener("change", event => {
      const value = event.target.value;
      if (value !== state[type].constraint) clearForConstraint(type, value);
      else syncConstraintButtons(value);
      updateDemoButton(type);
    });
    byId(`${type}-task-id`).addEventListener("input", () => clearStaleResult(type));
    byId(`${type}-demo-btn`).addEventListener("click", () => prepareDemo(type));
  }

  byId("vlm-provider-select").addEventListener("change", () => { updateProviderRequirements(); clearStaleResult("vlm"); });
  for (const id of ["vlm-model-name", "vlm-base-url", "vlm-api-key"]) byId(id).addEventListener("input", () => clearStaleResult("vlm"));
  byId("eval-constraint-picker").addEventListener("click", event => {
    const value = event.target.closest("button")?.dataset.constraint;
    if (value) selectConstraint(value);
  });
  for (const type of ["csv", "vlm"]) {
    tab(type).addEventListener("click", () => {
      if (activeType === type) return;
      resetType(activeType, { announce: false });
      resetType(type, { announce: false });
      syncConstraintButtons("");
      setActive(type);
      updateProviderRequirements();
      status(type, "idle", idleMessage(type));
    });
  }

  const providerSelect = byId("vlm-provider-select");
  for (const provider of config.providers) {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = provider.label;
    providerSelect.append(option);
  }
  byId("vlm-file-types").textContent = `One sample · ${config.fileTypes.video.extensions.join(" / ")}`;
  if (!config.BACKEND_URL.trim()) byId("eval-backend-note").textContent = "Evaluation backend is not connected. No result will be generated until the service is configured.";
  window.addEventListener("pagehide", clearVlmPrivateFields);
  setActive("csv");
  updateProviderRequirements();
})();
