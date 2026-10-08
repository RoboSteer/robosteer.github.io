# Level 2 Evaluation API contract

The static homepage at `https://robosteer.github.io/` calls a separate RoboSteer evaluation backend. Configure that service's HTTPS base URL only in `evaluation-config.js` as `BACKEND_URL` (no trailing slash needed). The current URL is a temporary Cloudflare Quick Tunnel and must be replaced there when a stable domain is available. A user-provided VLM `base_url` is a different value and must never be assigned to `BACKEND_URL`.

The frontend has two explicit internal modes. It starts in `official` mode and changes to `custom` only when the user selects **Use Your Own Case**. Mode is never inferred from whether an input is empty.

## Official examples

On initialization, the frontend requests:

`GET {BACKEND_URL}/api/level2/official-examples`

It uses the returned `examples` array as the only source of official example IDs and matches examples to the seven visible constraints through a centralized normalization function. The public fields used by the page are `id`, `constraint`, `task_id`, `display_name`, `description`, `steer_instruction`, and `evaluation_type`.

Evaluating the selected official example sends:

`POST {BACKEND_URL}/api/level2/official-examples/{example_id}/evaluate`

This request has no body and does not send Task ID, files, provider settings, model information, Base URL, API Key, or an unnecessary `Content-Type` header. CSV and video assets remain on the server. Official Order and Times credentials are held entirely by the backend; the frontend contains only explanatory display text and no official secret.

If loading the list fails, the page displays a retry action and keeps the custom upload path available. An official evaluation cannot be submitted without an example ID returned by the list endpoint.

## User-provided evaluations

Both custom evaluation routes use `multipart/form-data`. The browser sets the boundary and `Content-Type` automatically.

## CSV evaluation

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
