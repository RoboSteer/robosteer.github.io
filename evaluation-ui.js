(() => {
  "use strict";
  const config = window.ROBOOSTEER_EVALUATION_CONFIG;
  const service = window.RoboSteerEvaluationService;
  const byId = id => document.getElementById(id);
  if (!config || !service || !byId("evaluation")) return;

  const groups = {
    csv: { values: ["speed", "amplitude", "direction", "trajectory", "body_restrain"] },
    vlm: { values: ["order", "times"] }
  };
  const canonicalConstraints = Object.freeze({
    speed: "speed",
    amplitude: "amplitude",
    direction: "direction",
    trajectory: "trajectory",
    bodyrestrain: "body_restrain",
    order: "order",
    times: "times"
  });
  const csvSlots = Object.freeze({
    jointPos: { id: "joint-pos", expectedName: "joint_pos.csv" },
    bodyPos: { id: "body-pos", expectedName: "body_pos.csv" },
    bodyQuat: { id: "body-quat", expectedName: "body_quat.csv" }
  });
  const emptyCsvFiles = () => Object.fromEntries(Object.keys(csvSlots).map(slot => [slot, null]));
  const state = {
    csv: { files: emptyCsvFiles(), busy: false, constraint: "speed", customConstraint: "" },
    vlm: { file: null, busy: false, constraint: "order", customConstraint: "" }
  };
  const officialState = {
    loading: false,
    error: "",
    examples: [],
    byConstraint: new Map()
  };
  let evaluationMode = "official";
  let activeType = "csv";

  const tab = type => byId(type === "csv" ? "tab-csv" : "tab-vlm");
  const panel = type => byId(type === "csv" ? "panel-csv" : "panel-vlm");
  const form = type => byId(`${type}-evaluation-form`);
  const resultBox = type => byId(`${type}-result-box`);

  function normalizeConstraint(value) {
    const key = String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
    return canonicalConstraints[key] || "";
  }

  function typeForConstraint(value) {
    const constraint = normalizeConstraint(value);
    if (groups.csv.values.includes(constraint)) return "csv";
    if (groups.vlm.values.includes(constraint)) return "vlm";
    return "";
  }

  function currentOfficialExample(type) {
    const constraint = normalizeConstraint(state[type].constraint);
    return constraint ? officialState.byConstraint.get(constraint) || null : null;
  }

  function idleMessage(type) {
    if (evaluationMode === "official") {
      const example = currentOfficialExample(type);
      return example
        ? `${example.displayName || "Official example"} is ready. Click Evaluate to run the real evaluation.`
        : "Choose a constraint with an available official example.";
    }
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
    const headings = {
      idle: "Evaluation Output",
      "file-selected": "Files selected",
      validating: "Checking input",
      evaluating: "Evaluating…",
      "invalid-input": "Check your input"
    };
    heading.textContent = headings[name] || "Evaluation unavailable";
    const text = document.createElement("p");
    text.textContent = message;
    content.append(heading, text);
    box.append(content);
  }

  function showResult(type, response) {
    const box = resultBox(type);
    const result = response.result;
    box.dataset.state = result.satisfied === false ? "failure" : "success";
    box.replaceChildren();
    const wrap = document.createElement("div");
    wrap.className = "result-container";
    const header = document.createElement("div");
    header.className = "result-header";
    const title = document.createElement("strong");
    title.textContent = "Result";
    const context = document.createElement("span");
    context.className = "result-timestamp";
    context.textContent = `${String(response.constraint || "").replaceAll("_", " ")} · ${response.taskId || ""}`;
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
    const previous = activeType;
    activeType = type;
    if (previous === "vlm" && type !== "vlm") clearInput("vlm-api-key");
    for (const other of ["csv", "vlm"]) {
      const active = other === type;
      tab(other).classList.toggle("active", active);
      tab(other).setAttribute("aria-selected", String(active));
      panel(other).hidden = !active;
      panel(other).classList.toggle("active", active);
    }
  }

  function syncConstraintButtons(selected) {
    const normalized = normalizeConstraint(selected);
    byId("eval-constraint-picker").querySelectorAll("button").forEach(button => {
      button.setAttribute("aria-pressed", String(normalizeConstraint(button.dataset.constraint) === normalized));
    });
  }

  function renderOfficialExample(type) {
    const stateBox = byId(`${type}-official-state`);
    const message = byId(`${type}-official-state-message`);
    const retry = byId(`${type}-official-retry`);
    const content = byId(`${type}-official-content`);
    const example = currentOfficialExample(type);
    stateBox.hidden = false;
    content.hidden = true;
    retry.hidden = true;

    if (officialState.loading) {
      stateBox.dataset.state = "loading";
      message.textContent = "Loading the official example…";
    } else if (officialState.error) {
      stateBox.dataset.state = "error";
      message.textContent = officialState.error;
      retry.hidden = false;
    } else if (!state[type].constraint) {
      stateBox.dataset.state = "empty";
      message.textContent = "Choose a constraint to view its official example.";
    } else if (!example) {
      stateBox.dataset.state = "error";
      message.textContent = "No official example is available for this constraint. You can use your own case instead.";
    } else {
      stateBox.hidden = true;
      content.hidden = false;
      byId(`${type}-official-name`).textContent = example.displayName || "Official example";
      byId(`${type}-official-task-id`).value = example.taskId;
      byId(`${type}-official-description`).textContent = example.description || "No description provided.";
      byId(`${type}-official-instruction`).textContent = example.steerInstruction || "No steer instruction provided.";
      byId(`${type}-official-type`).textContent = example.evaluationType || (type === "csv" ? "CSV" : "Video");
    }
    updateControls(type);
  }

  function updateControls(type) {
    const busy = state[type].busy;
    const official = evaluationMode === "official";
    const exampleReady = Boolean(currentOfficialExample(type)) && !officialState.loading && !officialState.error;
    byId(`btn-eval-${type}`).disabled = busy || (official && !exampleReady);
    byId(`btn-use-custom-${type}`).hidden = !official;
    byId(`btn-use-official-${type}`).hidden = official;
    byId(`btn-reset-${type}`).hidden = official;
  }

  function announceCurrentContext(type) {
    status(type, "idle", idleMessage(type));
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
    if (!input) return;
    input.value = "";
    input.defaultValue = "";
  }

  function clearVlmPrivateFields() {
    clearInput("vlm-api-key");
    clearInput("vlm-model-name");
    clearInput("vlm-base-url");
  }

  function resetCustomInputs(type) {
    clearInput(`${type}-task-id`);
    clearUploads(type);
    if (type === "vlm") {
      clearVlmPrivateFields();
      byId("vlm-provider-select").value = "";
      updateProviderRequirements();
    }
  }

  function prepareCustomConstraint(type, constraint) {
    const normalized = normalizeConstraint(constraint);
    if (state[type].customConstraint !== normalized) {
      resetCustomInputs(type);
      state[type].customConstraint = normalized;
    }
  }

  function changeConstraint(type, value, { announce = true } = {}) {
    const constraint = normalizeConstraint(value);
    state[type].constraint = constraint;
    byId(`${type}-constraint-select`).value = constraint;
    if (evaluationMode === "custom") prepareCustomConstraint(type, constraint);
    if (type === activeType) syncConstraintButtons(constraint);
    renderOfficialExample(type);
    if (announce && type === activeType) announceCurrentContext(type);
  }

  function firstConstraintForType(type) {
    const fromBackend = officialState.examples.find(example => typeForConstraint(example.constraint) === type);
    return normalizeConstraint(fromBackend?.constraint) || groups[type].values[0];
  }

  function selectConstraint(value) {
    const constraint = normalizeConstraint(value);
    const type = typeForConstraint(constraint);
    if (!type) return;
    if (activeType !== type) setActive(type);
    changeConstraint(type, constraint);
    updateProviderRequirements();
  }

  function setMode(mode) {
    if (!new Set(["official", "custom"]).has(mode)) return;
    const leavingCustomVlm = evaluationMode === "custom" && mode === "official";
    evaluationMode = mode;
    document.querySelectorAll("[data-mode-section]").forEach(section => {
      section.hidden = section.dataset.modeSection !== mode;
    });
    if (mode === "custom") prepareCustomConstraint(activeType, state[activeType].constraint);
    if (leavingCustomVlm) clearInput("vlm-api-key");
    for (const type of ["csv", "vlm"]) updateControls(type);
    announceCurrentContext(activeType);
  }

  function clearStaleResult(type) {
    if (["success", "failure", "backend-error", "invalid-input"].includes(resultBox(type).dataset.state)) {
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
    if (!busy) updateControls(type);
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

  async function evaluateOfficial(type) {
    const example = currentOfficialExample(type);
    if (!example) {
      status(type, "invalid-input", "No official example is available for the selected constraint.");
      updateControls(type);
      return;
    }
    setBusy(type, true);
    status(type, "evaluating", "The official example is being evaluated…");
    try {
      const response = await service.evaluateOfficialExample(example);
      showResult(type, response);
    } catch (caught) {
      status(type, "backend-error", caught instanceof service.EvaluationError ? caught.message : "Evaluation failed. Please try again.");
    } finally {
      setBusy(type, false);
    }
  }

  async function evaluateCustom(type) {
    status(type, "validating", "Checking your input…");
    const constraint = normalizeConstraint(state[type].constraint);
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

  async function evaluate(type) {
    if (state[type].busy) return;
    if (evaluationMode === "official") await evaluateOfficial(type);
    else await evaluateCustom(type);
  }

  async function loadOfficialExamples() {
    if (officialState.loading) return;
    officialState.loading = true;
    officialState.error = "";
    for (const type of ["csv", "vlm"]) renderOfficialExample(type);
    try {
      const examples = await service.fetchOfficialExamples();
      const byConstraint = new Map();
      for (const example of examples) {
        const constraint = normalizeConstraint(example.constraint);
        if (!constraint || byConstraint.has(constraint)) continue;
        byConstraint.set(constraint, Object.freeze({ ...example, constraint }));
      }
      officialState.examples = [...byConstraint.values()];
      officialState.byConstraint = byConstraint;
      officialState.loading = false;
      if (!state.csv.constraint) state.csv.constraint = firstConstraintForType("csv");
      if (!state.vlm.constraint) state.vlm.constraint = firstConstraintForType("vlm");
      byId("csv-constraint-select").value = state.csv.constraint;
      byId("vlm-constraint-select").value = state.vlm.constraint;
      syncConstraintButtons(state[activeType].constraint);
      for (const type of ["csv", "vlm"]) renderOfficialExample(type);
      if (evaluationMode === "official") announceCurrentContext(activeType);
    } catch (caught) {
      officialState.loading = false;
      officialState.error = caught instanceof service.EvaluationError
        ? caught.message
        : "Official examples could not be loaded. Please try again.";
      for (const type of ["csv", "vlm"]) renderOfficialExample(type);
      if (evaluationMode === "official") status(activeType, "backend-error", officialState.error);
    }
  }

  for (const slot of Object.keys(csvSlots)) setupCsvSlot(slot);
  setupVideoFile();

  for (const type of ["csv", "vlm"]) {
    form(type).addEventListener("submit", event => { event.preventDefault(); evaluate(type); });
    byId(`btn-reset-${type}`).addEventListener("click", () => {
      resetCustomInputs(type);
      state[type].constraint = "";
      state[type].customConstraint = "";
      byId(`${type}-constraint-select`).value = "";
      syncConstraintButtons("");
      status(type, "idle", idleMessage(type));
    });
    byId(`btn-use-custom-${type}`).addEventListener("click", () => setMode("custom"));
    byId(`btn-use-official-${type}`).addEventListener("click", () => setMode("official"));
    byId(`${type}-official-retry`).addEventListener("click", loadOfficialExamples);
    byId(`${type}-constraint-select`).addEventListener("change", event => changeConstraint(type, event.target.value));
    byId(`${type}-task-id`).addEventListener("input", () => clearStaleResult(type));
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
      setActive(type);
      if (!state[type].constraint) changeConstraint(type, firstConstraintForType(type), { announce: false });
      else syncConstraintButtons(state[type].constraint);
      if (evaluationMode === "custom") prepareCustomConstraint(type, state[type].constraint);
      updateProviderRequirements();
      announceCurrentContext(type);
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
  byId("csv-constraint-select").value = state.csv.constraint;
  byId("vlm-constraint-select").value = state.vlm.constraint;
  setActive("csv");
  setMode("official");
  syncConstraintButtons(state.csv.constraint);
  updateProviderRequirements();
  loadOfficialExamples();
})();
