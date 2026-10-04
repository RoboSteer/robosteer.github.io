// Edit this file when the evaluation backend and its supported providers are ready.
window.ROBOOSTEER_EVALUATION_CONFIG = Object.freeze({
  BACKEND_URL: "",
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
  // Add only complete, real examples hosted on this site. CSV demos require all
  // three assets from one generated sample; video demos require one video asset.
  // Example CSV shape:
  // speed: {
  //   taskId: "task_xxx",
  //   csvAssetUrls: {
  //     jointPos: "assets/evaluation/speed/joint_pos.csv",
  //     bodyPos: "assets/evaluation/speed/body_pos.csv",
  //     bodyQuat: "assets/evaluation/speed/body_quat.csv"
  //   }
  // }
  demos: {
    speed: { taskId: "", csvAssetUrls: { jointPos: "", bodyPos: "", bodyQuat: "" } },
    amplitude: { taskId: "", csvAssetUrls: { jointPos: "", bodyPos: "", bodyQuat: "" } },
    direction: { taskId: "", csvAssetUrls: { jointPos: "", bodyPos: "", bodyQuat: "" } },
    trajectory: { taskId: "", csvAssetUrls: { jointPos: "", bodyPos: "", bodyQuat: "" } },
    body_restrain: { taskId: "", csvAssetUrls: { jointPos: "", bodyPos: "", bodyQuat: "" } },
    order: { taskId: "", videoAssetUrl: "" },
    times: { taskId: "", videoAssetUrl: "" }
  },
  // null means that the front end has no independent size limit.
  maxFileBytes: null
});
