// Edit this file when the evaluation backend and its supported providers are ready.
window.ROBOOSTEER_EVALUATION_CONFIG = Object.freeze({
  BACKEND_URL: "https://divisions-pace-meditation-www.trycloudflare.com",
  providers: [
    { id: "openai", label: "OpenAI" },
    { id: "google", label: "Google Gemini" },
    { id: "anthropic", label: "Anthropic" },
    { id: "custom_openai_compatible", label: "Custom (OpenAI-compatible)", requiresBaseUrl: true }
  ],
  fileTypes: {
    csv: { extensions: [".csv"], mimeTypes: ["text/csv", "application/csv", "application/vnd.ms-excel"] },
    video: { extensions: [".mp4", ".webm", ".mov"], mimeTypes: ["video/mp4", "video/webm", "video/quicktime"] }
  },
  // null means that the front end has no independent size limit.
  maxFileBytes: null
});
