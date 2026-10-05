(() => {
  "use strict";
  const csvConstraints = new Set(["speed", "amplitude", "direction", "trajectory", "body_restrain"]);
  const videoConstraints = new Set(["order", "times"]);
  const csvDemoSlots = Object.freeze({
    jointPos: "joint_pos.csv",
    bodyPos: "body_pos.csv",
    bodyQuat: "body_quat.csv"
  });

  class EvaluationError extends Error {
    constructor(code, message) { super(message); this.name = "EvaluationError"; this.code = code; }
  }

  function sameSiteAssetUrl(value) {
    let assetUrl;
    try { assetUrl = new URL(value, document.baseURI); }
    catch { throw new EvaluationError("DEMO_UNAVAILABLE", "This example asset URL is invalid."); }
    if (assetUrl.origin !== new URL(document.baseURI).origin || !["http:", "https:"].includes(assetUrl.protocol)) {
      throw new EvaluationError("DEMO_UNAVAILABLE", "Example assets must be hosted on this website.");
    }
    return assetUrl;
  }

  async function fetchDemoFile(value, filename) {
    const assetUrl = sameSiteAssetUrl(value);
    let response;
    try { response = await fetch(assetUrl.href); }
    catch { throw new EvaluationError("DEMO_UNAVAILABLE", "The example asset could not be loaded."); }
    if (!response.ok) throw new EvaluationError("DEMO_UNAVAILABLE", "The example asset could not be loaded.");
    const blob = await response.blob();
    return new File([blob], filename || assetUrl.pathname.split("/").pop(), { type: blob.type });
  }

  async function loadDemo(constraint) {
    const csv = csvConstraints.has(constraint);
    if (!csv && !videoConstraints.has(constraint)) {
      throw new EvaluationError("INVALID_CONSTRAINT", "Choose a valid constraint.");
    }
    const demo = window.ROBOOSTEER_EVALUATION_CONFIG?.demos?.[constraint];
    if (!demo?.taskId?.trim()) throw new EvaluationError("DEMO_UNAVAILABLE", "This example is not configured yet.");

    if (csv) {
      const urls = demo.csvAssetUrls;
      if (!urls || Object.keys(csvDemoSlots).some(slot => !urls[slot]?.trim())) {
        throw new EvaluationError("DEMO_UNAVAILABLE", "A complete three-file example is not configured yet.");
      }
      const entries = await Promise.all(Object.entries(csvDemoSlots).map(async ([slot, filename]) => {
        const file = await fetchDemoFile(urls[slot], filename);
        return [slot, file];
      }));
      return { taskId: demo.taskId.trim(), files: Object.fromEntries(entries) };
    }

    if (!demo.videoAssetUrl?.trim()) throw new EvaluationError("DEMO_UNAVAILABLE", "This example is not configured yet.");
    return {
      taskId: demo.taskId.trim(),
      file: await fetchDemoFile(demo.videoAssetUrl)
    };
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
    const missing = Object.keys(csvDemoSlots).filter(slot => !files?.[slot]);
    if (missing.length) {
      const names = missing.map(slot => csvDemoSlots[slot]);
      throw new EvaluationError("INVALID_INPUT", `Choose ${names.join(", ")}.`);
    }
  }

  function safeBackendMessage(raw, apiKey, fallback) {
    return apiKey && raw.includes(apiKey) ? fallback : raw;
  }

  async function request(kind, { taskId, constraint, files, file, provider, apiKey, baseUrl, modelName }) {
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

    const base = window.ROBOOSTEER_EVALUATION_CONFIG?.BACKEND_URL?.trim().replace(/\/+$/, "");
    if (!base) throw new EvaluationError("BACKEND_UNAVAILABLE", "Evaluation backend is not connected yet.");

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
    try {
      response = await fetch(`${base}/api/level2/evaluate/${kind}`, { method: "POST", body });
    } catch {
      throw new EvaluationError("BACKEND_UNAVAILABLE", "Evaluation service is unreachable. Please try again later.");
    }
    let data;
    try { data = await response.json(); }
    catch { throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unreadable response."); }

    if (!response.ok || data?.success === false) {
      const fallback = "Evaluation failed. Please try again.";
      const raw = typeof data?.error?.message === "string" ? data.error.message : fallback;
      throw new EvaluationError(data?.error?.code || "BACKEND_ERROR", safeBackendMessage(raw, requestApiKey, fallback));
    }
    if (data?.success !== true || !data.result || typeof data.result !== "object" || Array.isArray(data.result)) {
      throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    }
    const result = data.result;
    if (result.satisfied != null && typeof result.satisfied !== "boolean") throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    if (result.score != null && (typeof result.score !== "number" || !Number.isFinite(result.score))) throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    if (result.message != null && typeof result.message !== "string") throw new EvaluationError("INVALID_RESPONSE", "Evaluation service returned an unexpected result.");
    const safeMessage = result.message ? safeBackendMessage(result.message, requestApiKey, "Evaluation completed.") : result.message;
    return {
      taskId: typeof data.task_id === "string" ? data.task_id : taskId.trim(),
      constraint: typeof data.constraint === "string" ? data.constraint : constraint,
      result: { satisfied: result.satisfied, score: result.score, message: safeMessage }
    };
  }

  window.RoboSteerEvaluationService = Object.freeze({
    EvaluationError,
    loadDemo,
    normalizeBaseUrl,
    evaluateCsv: fields => request("csv", fields),
    evaluateVideo: fields => request("video", fields)
  });
})();
