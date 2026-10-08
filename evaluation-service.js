(() => {
  "use strict";
  const csvConstraints = new Set(["speed", "amplitude", "direction", "trajectory", "body_restrain"]);
  const videoConstraints = new Set(["order", "times"]);
  const csvFileNames = Object.freeze({
    jointPos: "joint_pos.csv",
    bodyPos: "body_pos.csv",
    bodyQuat: "body_quat.csv"
  });

  class EvaluationError extends Error {
    constructor(code, message) { super(message); this.name = "EvaluationError"; this.code = code; }
  }

  function backendUrl() {
    const value = window.ROBOOSTEER_EVALUATION_CONFIG?.BACKEND_URL?.trim().replace(/\/+$/, "");
    if (!value) throw new EvaluationError("BACKEND_UNAVAILABLE", "Evaluation backend is not connected yet.");
    return value;
  }

  function normalizeBaseUrl(value) {
    const raw = value?.trim() || "";
    if (!raw) return "";
    let parsed;
    try { parsed = new URL(raw); }
    catch { throw new EvaluationError("INVALID_INPUT", "Enter a valid Base URL."); }
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new EvaluationError("INVALID_INPUT", "Base URL must use HTTP or HTTPS.");
    }
    const localPage = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname) || window.location.protocol === "file:";
    if (!localPage && parsed.protocol !== "https:") {
      throw new EvaluationError("INVALID_INPUT", "Base URL must use HTTPS on the published website.");
    }
    if (parsed.username || parsed.password) {
      throw new EvaluationError("INVALID_INPUT", "Base URL must not contain a username or password.");
    }
    if (parsed.search || parsed.hash) {
      throw new EvaluationError("INVALID_INPUT", "Base URL must not contain a query string or fragment.");
    }
    if (/(?:\/chat\/completions|\/responses|\/messages|:generateContent)\/?$/i.test(parsed.pathname)) {
      throw new EvaluationError("INVALID_INPUT", "Enter the API root as Base URL, not a complete request path.");
    }
    return parsed.href.replace(/\/+$/, "");
  }

  function requireCsvFiles(files) {
    const missing = Object.keys(csvFileNames).filter(slot => !files?.[slot]);
    if (missing.length) {
      const names = missing.map(slot => csvFileNames[slot]);
      throw new EvaluationError("INVALID_INPUT", `Choose ${names.join(", ")}.`);
    }
  }

  function safeBackendMessage(raw, apiKey, fallback) {
    if (typeof raw !== "string") return fallback;
    const message = raw.trim();
    const looksSensitive = (apiKey && message.includes(apiKey))
      || message.length > 600
      || /(?:^|\n)\s*(?:at\s+|traceback\b|file\s+["'])/i.test(message)
      || /(?:^|[\s"'(])\/(?:home|root|srv|var|opt|tmp|workspace)\//i.test(message)
      || /\b[A-Z]:\\(?:Users|Windows|Program Files)\\/i.test(message);
    return !message || looksSensitive ? fallback : message;
  }

  async function readJson(response, fallbackMessage) {
    try { return await response.json(); }
    catch { throw new EvaluationError("INVALID_RESPONSE", fallbackMessage); }
  }

  async function handleEvaluationResponse(response, fallback, apiKey = "") {
    const data = await readJson(response, "Evaluation service returned an unreadable response.");
    if (!response.ok || data?.success === false) {
      const fallbackMessage = "Evaluation failed. Please try again.";
      const raw = typeof data?.error?.message === "string" ? data.error.message : fallbackMessage;
      throw new EvaluationError(data?.error?.code || "BACKEND_ERROR", safeBackendMessage(raw, apiKey, fallbackMessage));
    }
    if (data?.success !== true || !data.result || typeof data.result !== "object" || Array.isArray(data.result)) {
      throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    }
    const result = data.result;
    if (result.satisfied != null && typeof result.satisfied !== "boolean") throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    if (result.score != null && (typeof result.score !== "number" || !Number.isFinite(result.score))) throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    if (result.message != null && typeof result.message !== "string") throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    const safeMessage = result.message ? safeBackendMessage(result.message, apiKey, "Evaluation completed.") : result.message;
    return {
      taskId: typeof data.task_id === "string" ? data.task_id : fallback.taskId,
      constraint: typeof data.constraint === "string" ? data.constraint : fallback.constraint,
      result: { satisfied: result.satisfied, score: result.score, message: safeMessage }
    };
  }

  async function fetchOfficialExamples() {
    let response;
    try { response = await fetch(`${backendUrl()}/api/level2/official-examples`); }
    catch { throw new EvaluationError("BACKEND_UNAVAILABLE", "Official examples could not be loaded. The evaluation service may be unavailable."); }
    const data = await readJson(response, "The official examples response could not be read.");
    if (!response.ok || data?.success === false) {
      const fallback = "Official examples could not be loaded.";
      const message = safeBackendMessage(data?.error?.message, "", fallback);
      throw new EvaluationError(data?.error?.code || "BACKEND_ERROR", message);
    }
    if (data?.success !== true || !Array.isArray(data.examples)) {
      throw new EvaluationError("INVALID_RESPONSE", "The evaluation service returned an invalid official examples list.");
    }
    return data.examples.map(item => {
      if (!item || typeof item.id !== "string" || !item.id.trim() || typeof item.constraint !== "string" || !item.constraint.trim()) {
        throw new EvaluationError("INVALID_RESPONSE", "The evaluation service returned an invalid official example.");
      }
      return Object.freeze({
        id: item.id.trim(),
        constraint: item.constraint.trim(),
        taskId: typeof item.task_id === "string" ? item.task_id.trim() : "",
        displayName: typeof item.display_name === "string" ? item.display_name.trim() : "",
        description: typeof item.description === "string" ? item.description.trim() : "",
        steerInstruction: typeof item.steer_instruction === "string" ? item.steer_instruction.trim() : "",
        evaluationType: typeof item.evaluation_type === "string" ? item.evaluation_type.trim() : ""
      });
    });
  }

  async function evaluateOfficialExample(example) {
    if (!example?.id) throw new EvaluationError("EXAMPLE_UNAVAILABLE", "No official example is available for this constraint.");
    let response;
    try {
      response = await fetch(`${backendUrl()}/api/level2/official-examples/${encodeURIComponent(example.id)}/evaluate`, { method: "POST" });
    } catch {
      throw new EvaluationError("BACKEND_UNAVAILABLE", "Evaluation service is unreachable. Please try again later.");
    }
    return handleEvaluationResponse(response, { taskId: example.taskId, constraint: example.constraint });
  }

  async function requestCustom(kind, { taskId, constraint, files, file, provider, apiKey, baseUrl, modelName }) {
    const allowed = kind === "csv" ? csvConstraints : videoConstraints;
    const requestApiKey = apiKey?.trim() || "";
    if (!allowed.has(constraint)) throw new EvaluationError("INVALID_CONSTRAINT", "Choose a valid constraint.");
    if (!taskId?.trim()) throw new EvaluationError("INVALID_INPUT", "Enter a Task ID.");

    let normalizedBaseUrl = "";
    if (kind === "csv") {
      requireCsvFiles(files);
    } else {
      if (!file) throw new EvaluationError("INVALID_INPUT", "Choose a video file.");
      if (!provider) throw new EvaluationError("INVALID_INPUT", "Choose a VLM provider.");
      if (!modelName?.trim()) throw new EvaluationError("INVALID_INPUT", "Enter a Model Name.");
      if (!requestApiKey) throw new EvaluationError("INVALID_INPUT", "Enter an API Key.");
      normalizedBaseUrl = normalizeBaseUrl(baseUrl);
      const providerConfig = window.ROBOOSTEER_EVALUATION_CONFIG?.providers?.find(item => item.id === provider);
      if (providerConfig?.requiresBaseUrl && !normalizedBaseUrl) {
        throw new EvaluationError("INVALID_INPUT", "Enter a Base URL for the custom provider.");
      }
    }

    const body = new FormData();
    body.append("task_id", taskId.trim());
    body.append("constraint", constraint);
    if (kind === "csv") {
      body.append("joint_pos_file", files.jointPos, files.jointPos.name);
      body.append("body_pos_file", files.bodyPos, files.bodyPos.name);
      body.append("body_quat_file", files.bodyQuat, files.bodyQuat.name);
    } else {
      body.append("provider", provider);
      body.append("model_name", modelName.trim());
      if (normalizedBaseUrl) body.append("base_url", normalizedBaseUrl);
      body.append("api_key", requestApiKey);
      body.append("file", file, file.name);
    }

    let response;
    try { response = await fetch(`${backendUrl()}/api/level2/evaluate/${kind}`, { method: "POST", body }); }
    catch { throw new EvaluationError("BACKEND_UNAVAILABLE", "Evaluation service is unreachable. Please try again later."); }
    return handleEvaluationResponse(response, { taskId: taskId.trim(), constraint }, requestApiKey);
  }

  window.RoboSteerEvaluationService = Object.freeze({
    EvaluationError,
    fetchOfficialExamples,
    evaluateOfficialExample,
    normalizeBaseUrl,
    evaluateCsv: fields => requestCustom("csv", fields),
    evaluateVideo: fields => requestCustom("video", fields)
  });
})();
