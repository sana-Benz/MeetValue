# Implementation Plan: MeetValue MVP (Optimized)

## Overview

Minimal task list to ship a working, demoable MeetValue app. No automated test suite, no history, no interactive recalculation, no keyword-parsing of Claude's output (structured JSON instead). Every task here is required for a working demo — nothing marked optional, because at this scope everything left in already earns its place.

## Tasks

- [x] 1. Project structure
  - [x] 1.1 Create folders: `backend/functions/calculate_cost/`, `backend/functions/get_recommendations/`, `backend/shared/`, `frontend/css/`, `frontend/js/`, `infrastructure/`
  - [x] 1.2 Create `backend/requirements.txt` with `boto3`
  - [x] 1.3 Create `backend/shared/constants.py` with hourly rates (junior: 50, mid-level: 100, senior: 200, executive: 400) and the list of valid seniority levels

- [x] 2. Cost Calculator Lambda (`backend/functions/calculate_cost/handler.py`)
  - [x] 2.1 Parse request body (subject, duration_minutes, attendees)
  - [x] 2.2 Validate: duration 15–240, attendees non-empty, each seniority valid → HTTP 400 with a clear message on any failure
  - [x] 2.3 Calculate: `cost_contribution = hourly_rate × (duration_minutes / 60)` per attendee, `total_cost = sum(cost_contribution)`
  - [x] 2.4 Return `{ total_cost, breakdown: [{attendee_name, seniority, hourly_rate, cost_contribution}] }` as HTTP 200 JSON
  - [x] 2.5 Wrap in try/except → unexpected errors return HTTP 500, generic message (no stack trace)

- [x] 3. Shared Bedrock client (`backend/shared/bedrock_client.py`)
  - [x] 3.1 `get_bedrock_client()` — boto3 `bedrock-runtime` client, region from `BEDROCK_REGION` env var
  - [x] 3.2 `call_bedrock_converse(prompt, max_tokens=500)` — calls the Converse API with `BEDROCK_MODEL_ID` from env, returns the response text, raises on failure (no retry logic — keep it simple, let the caller handle the error)

- [x] 4. AI Recommender Lambda (`backend/functions/get_recommendations/handler.py`)
  - [x] 4.1 Parse request body (subject, duration_minutes, total_cost, attendees)
  - [x] 4.2 Build a prompt that instructs Claude to respond with **JSON only**, e.g.:
    ```
    Return ONLY valid JSON, no other text, in this exact format:
    [{"category": "partial_attendance" | "duration_reduction" | "consolidation",
      "affected_attendee_names": [string],
      "duration_reduction_minutes": number,
      "reasoning": string}]
    Meeting: {subject}, {duration_minutes} min, ${total_cost}, attendees: {list}
    Suggest 2-4 items.
    ```
  - [x] 4.3 Call `call_bedrock_converse()`, then `json.loads()` the response
  - [x] 4.4 For each item, calculate `estimated_savings`:
    - partial_attendance / consolidation → sum of `hourly_rate × duration_hours` for each name in `affected_attendee_names`
    - duration_reduction → `duration_reduction_minutes / 60 × sum(all attendees' hourly_rate)`
  - [x] 4.5 Build response: `{ recommendations: [{category, suggestion: reasoning, estimated_savings}] }`
  - [x] 4.6 On `json.loads()` failure or missing fields → return 2 hardcoded default recommendations instead of erroring (e.g., "Consider making junior attendees optional", "Consider shortening the meeting by 15 minutes") with `estimated_savings: 0`
  - [x] 4.7 Wrap the Bedrock call in try/except → on failure return HTTP 503 with `{"error": "Recommendations unavailable. Here's your cost breakdown."}`

- [x] 5. Checkpoint — test both Lambdas locally
  - Run each handler with a hardcoded sample event (no SAM deploy yet)
  - Confirm calculate_cost returns correct numbers by hand-checking one example
  - Confirm get_recommendations returns valid JSON with Bedrock, and returns defaults when you force a JSON parse failure

- [ ] 6. SAM template (`infrastructure/template.yaml`)
  - [x] 6.1 `AWS::Serverless::Api` with `Cors: AllowOrigin: "'*'"`, `AllowMethods: "'POST,OPTIONS'"`, `AllowHeaders: "'Content-Type'"`
  - [x] 6.2 `AWS::Serverless::Function` for `calculate_cost` — python3.12, timeout 10, memory 128, env vars for rates, `Events: Api POST /calculate-cost` — no extra `Policies:` (default minimal role)
  - [x] 6.3 `AWS::Serverless::Function` for `get_recommendations` — same base config, env vars `BEDROCK_MODEL_ID=anthropic.claude-haiku-4-5-20251001-v1:0`, `BEDROCK_REGION=us-east-1`, `MAX_TOKENS=500`, `Events: Api POST /get-recommendations`, `Policies:` scoped to `bedrock:InvokeModel` on that exact model ARN only
  - [ ] 6.4 `AWS::S3::Bucket` for the frontend (`meetcost-frontend-${AWS::AccountId}`), `WebsiteConfiguration` with `index.html`, public read via bucket policy
  - [ ] 6.5 Outputs: `FrontendBucketUrl`, `ApiEndpoint`

- [x] 7. Frontend (`frontend/index.html`, `css/style.css`, `js/app.js`)
  - [x] 7.1 One HTML page: subject input, duration input (15–240, step 15), attendee rows (name + seniority dropdown) with an "Add Attendee" button, a "Calculate" button, and result/error containers (hidden by default)
  - [x] 7.2 Minimal responsive CSS — flexbox layout, readable on mobile, large bold styling for the cost headline
  - [x] 7.3 `app.js`:
    - Client-side validation (subject non-empty, duration in range, ≥1 attendee) before calling the API
    - `POST /calculate-cost` → on success, display `"This meeting costs your company $X"` + breakdown table
    - Immediately after, `POST /get-recommendations` → on success, list recommendations with savings; on failure, show the fallback message but keep the cost visible
    - One loading indicator shown during both calls, hidden on completion or error
    - `API_BASE_URL` as a single constant at the top of the file, to be replaced after deployment

- [ ] 8. Deploy
  - [ ] 8.1 `sam deploy --guided` from `infrastructure/` (stack name `meetcost-stack`, region `us-east-1`) — note the `ApiEndpoint` and `FrontendBucketUrl` outputs
  - [ ] 8.2 Paste the real `ApiEndpoint` into `API_BASE_URL` in `app.js`
  - [ ] 8.3 `aws s3 sync frontend/ s3://meetcost-frontend-<account-id>/`
  - [ ] 8.4 Open `FrontendBucketUrl` in a browser, confirm no CORS errors in the console

- [ ] 9. End-to-end manual check (replaces automated tests for MVP scope)
  - [ ] 9.1 Happy path: 1 junior + 1 executive, 60 min → verify displayed total = $450, breakdown sums correctly
  - [ ] 9.2 Validation: submit with 0 attendees → clear inline error, no API call made
  - [ ] 9.3 AI path: verify recommendations appear with plausible savings amounts
  - [ ] 9.4 Failure path: temporarily break `BEDROCK_MODEL_ID` (typo it), redeploy, confirm the fallback message shows and cost is still visible — then fix it and redeploy
  - [ ] 9.5 Mobile check: open the site on a phone or narrow browser window, confirm it's usable

- [ ] 10. Demo & submission prep
  - [ ] 10.1 Short README: what it does, architecture diagram (text is fine), how to redeploy, screenshot of the app
  - [ ] 10.2 Screenshot or short screen recording of Kiro generating code tied to this project, for the "coding agent connection" proof
  - [ ] 10.3 Pick one clear demo example (e.g., 4 attendees, 1 hour, ~$750) to run live or record

## Explicitly cut from MVP (do only if time remains after step 10)
- Any automated unit/integration test suite (pytest, Jest)
- DynamoDB storage / meeting history
- Interactive "apply recommendation and recalculate" button
- Frontend retry-with-backoff logic
- Per-recommendation granular savings breakdown beyond the simple formula in 4.4
- Tightening CORS from `*` to the exact S3 origin

## Cost/complexity guardrails baked into this plan
- Claude Haiku 4.5 only, `max_tokens=500`, no retries → bounded, predictable Bedrock spend
- No DynamoDB, no provisioned anything — only pay-per-invocation Lambda + pay-per-request Bedrock
- Structured JSON output from Claude removes the fragile keyword-parsing that was the main source of bugs in the original plan
- Two Lambda functions, two IAM roles, one SAM template, one HTML page — no framework, no build step, nothing to configure beyond what's listed above

## Notes

- No task in this plan is marked optional (`*`) — at this reduced MVP scope, everything remaining is required for a working demo
- Backend has no automated test suite by design; step 9 (manual end-to-end check) replaces it to save time
- The Bedrock model ID (`anthropic.claude-haiku-4-5-20251001-v1:0`) must be double-checked against the Bedrock console at deploy time in case of future model updates
- Steps 1–5 (backend) and step 7 (frontend) can be built in parallel if working with a partner; steps 6, 8, 9, 10 depend on both being done first
- If still short on time after step 8, prioritize step 9.1–9.3 (happy path + AI path) over 9.4–9.5 (failure path + mobile) — a working demo matters more than exhaustive edge-case coverage

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.2", "1.3"]
    },
    {
      "id": 1,
      "tasks": ["2.1", "3.1", "7.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "3.2", "7.2"]
    },
    {
      "id": 3,
      "tasks": ["2.4", "2.5", "4.1", "7.3"]
    },
    {
      "id": 4,
      "tasks": ["4.2", "4.3"]
    },
    {
      "id": 5,
      "tasks": ["4.4", "4.5", "4.6", "4.7"]
    },
    {
      "id": 6,
      "tasks": ["5"]
    },
    {
      "id": 7,
      "tasks": ["6.1", "6.2", "6.3"]
    },
    {
      "id": 8,
      "tasks": ["6.4", "6.5"]
    },
    {
      "id": 9,
      "tasks": ["8.1"]
    },
    {
      "id": 10,
      "tasks": ["8.2", "8.3", "8.4"]
    },
    {
      "id": 11,
      "tasks": ["9.1", "9.2", "9.3", "9.4", "9.5"]
    },
    {
      "id": 12,
      "tasks": ["10.1", "10.2", "10.3"]
    }
  ]
}
```