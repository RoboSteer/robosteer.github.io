# Level 2 Evaluation API contract

> **Integration status:** this document describes the frontend contract implemented by the static website. The evaluation backend has **not yet been adapted** to accept the new three-file CSV payload or the user-selected VLM provider settings. Do not represent these requests as supported by a live service until the next backend phase implements and verifies the same contract.

The static homepage at `https://robosteer.github.io/` calls a separate RoboSteer evaluation backend. Configure that service's HTTPS base URL in `evaluation-config.js` as `BACKEND_URL` (no trailing slash needed). A user-provided VLM `base_url` is a different value: it identifies the model service that the evaluation backend should call and must never be assigned to `BACKEND_URL`.

Both evaluation routes use `multipart/form-data`. The browser sets the boundary and `Content-Type` automatically.

## CSV evaluation

Proposed route for the next backend phase:

`POST {BACKEND_URL}/api/level2/evaluate/csv`

| Field | Type | Requirement |
| --- | --- | --- |
| `task_id` | text | Nonempty RoboSteer benchmark Task ID |
| `constraint` | text | One of `speed`, `amplitude`, `direction`, `trajectory`, `body_restrain` |
| `joint_pos_file` | file | Nonempty `.csv` uploaded in the `joint_pos.csv` slot |
| `body_pos_file` | file | Nonempty `.csv` uploaded in the `body_pos.csv` slot |
| `body_quat_file` | file | Nonempty `.csv` uploaded in the `body_quat.csv` slot |

All three files must come from the same generated motion sample and include a header plus at least two valid data frames. The evaluation loader's unified motion representation is:

`[root xyz, root quaternion wxyz, 29 joint positions]`

The upload slot determines the semantic meaning of each file. The frontend warns when a local filename differs from the expected filename, but it does not silently move the file to a different field.

The frontend checks only that all three files are selected, nonempty, within any configured size limit, and use the `.csv` extension and an accepted CSV MIME type. The backend remains authoritative for headers, column counts, numeric values, quaternion validity, frame alignment, and using the shortest common frame count. The browser does not calculate IR₂.

All five CSV constraints require the unified three-file sample even though each score may use only part of it:

- Speed uses the shortest shared frame count.
- Amplitude primarily reads joint angles.
- Direction primarily reads root position and root orientation.
- Trajectory primarily reads root position.
- Body Restrain performs kinematic calculation on the assembled motion.

Task metadata, reference motion, and other server-side resources may also be required.

## Video + VLM evaluation

Proposed route for the next backend phase:

`POST {BACKEND_URL}/api/level2/evaluate/video`

| Field | Type | Requirement |
| --- | --- | --- |
| `task_id` | text | Nonempty RoboSteer benchmark Task ID |
| `constraint` | text | `order` or `times` |
| `provider` | text | `openai`, `google`, `anthropic`, or `custom_openai_compatible` |
| `model_name` | text | Nonempty model ID recognized by the selected provider or compatible service |
| `base_url` | text | Required for `custom_openai_compatible`; optional for preset providers |
| `api_key` | text | Nonempty user-provided key, used for this request only |
| `file` | file | One nonempty model-output video |

When a preset provider leaves `base_url` blank, the frontend omits the field. The future backend should then use its configured official default. When present, `base_url` is normalized by trimming whitespace and trailing slashes. The published frontend accepts only HTTPS and rejects credentials embedded in the URL, query strings, fragments, and obvious complete request paths such as `/chat/completions`. Local preview may use HTTP for localhost. These browser checks are not a security boundary: the backend must independently validate the URL and its resolved network target before making any request.

The current version requires an API Key for every provider, including private compatible services. Supporting keyless private services requires a separate frontend and backend contract change.

The API Key is held only long enough to create the current request. The frontend does not put it in a URL, log it, save it to local storage, or write it to static configuration. It clears the input after submission, reset, leaving the VLM form, and validation or request failure. Error messages must never echo the key. Model Name and Base URL are not persisted by the webpage.

The existing local `scripts/level2/evaluate_order.py` and `evaluate_times.py` use server-configured VLM model and endpoint parameters. They do not yet implement arbitrary provider, Base URL, Model Name, or API Key values from this web form.

## Accepted frontend file types

`evaluation-config.js` accepts `.csv` for each CSV slot and `.mp4`, `.webm`, or `.mov` for video. `maxFileBytes` is `null` until an agreed upload limit is available. Coordinate actual codec support and any size limit with the backend before launch.

## Responses

Successful JSON response (HTTP 2xx):

```json
{
  "success": true,
  "task_id": "task_xxx",
  "constraint": "speed",
  "result": {
    "satisfied": true,
    "score": 0.87,
    "message": "Constraint satisfied."
  }
}
```

`result.satisfied` is a boolean when present. `result.score` is a finite number or `null`; `result.message` is a string or `null`. The frontend omits absent or null result fields. Additional response fields may be included; the UI does not depend on them. The backend should define the meaning and range of each score, since the frontend displays the number without converting it to a percentage.

Failure JSON response (appropriate HTTP 4xx/5xx):

```json
{
  "success": false,
  "error": { "code": "INVALID_TASK_ID", "message": "Task ID was not found." }
}
```

Use short, user-safe error messages. The backend must resolve benchmark task and reference data from `task_id`, perform all authoritative CSV validation and evaluation, and make all VLM/API calls. Never persist or log a user's API Key or echo it in errors. Allow CORS requests from `https://robosteer.github.io` after deployment.
