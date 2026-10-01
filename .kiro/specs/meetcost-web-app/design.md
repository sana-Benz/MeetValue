# MeetValue Technical Design Document

## Overview

MeetValue is a serverless web application that calculates the real-time cost of team meetings and provides AI-powered recommendations to reduce those costs. The system consists of three main components:

1. **Frontend**: Static HTML/CSS/JavaScript interface hosted on Amazon S3
2. **Backend**: Two AWS Lambda functions (calculate_cost, get_recommendations) coordinated through Amazon API Gateway
3. **AI Layer**: Amazon Bedrock integration using Claude Haiku 4.5 for cost-reduction recommendations

The architecture is deliberately simple and stateless to minimize complexity during the hackathon while remaining scalable and cost-effective on AWS. No persistence layer (DynamoDB) is required for MVP scope.

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    Frontend (S3 Static Website)                          │   │
│  │  - HTML form (meeting details, attendees)               │   │
│  │  - JavaScript (form logic, API calls, rendering)        │   │
│  │  - CSS (responsive design, mobile-friendly)             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │ fetch() over HTTPS (CORS-enabled)
                              ↓
            ┌─────────────────────────────────┐
            │      API Gateway (REST)         │
            │  - POST /calculate-cost         │
            │  - POST /get-recommendations    │
            │  - CORS enabled on both         │
            └────┬────────────────────────┬───┘
                 │                        │
         ┌───────↓────────┐      ┌────────↓──────┐
         │  Lambda: Cost  │      │  Lambda: AI   │
         │  Calculator    │      │ Recommender   │
         │ (basic role)   │      │ (+ Bedrock    │
         │                │      │   scoped role)│
         └────────────────┘      └────────┬──────┘
                                           │
                             ┌─────────────↓──────────┐
                             │  Bedrock (Claude       │
                             │  Haiku 4.5)            │
                             └────────────────────────┘
```

Note: each Lambda has its **own** execution role, not a shared one. Only the AI Recommender's role includes Bedrock permissions — Cost Calculator never needs it.

### Data Flow Diagram

**Cost Calculation Flow:**
```
User Input → Form Validation → POST /calculate-cost → Lambda (calculate_cost)
  ↓
Parse meeting data → Calculate costs by attendee → Sum total cost
  ↓
Return: { total_cost, breakdown: [{ attendee, role, hourly_rate, cost }] }
  ↓
Frontend renders cost headline and breakdown
```

**Recommendation Flow:**
```
Cost Calculation Complete → POST /get-recommendations → Lambda (get_recommendations)
  ↓
Build prompt from meeting context → Call Bedrock Converse API (max_tokens: 500)
  ↓
Parse Claude response → Extract recommendations (partial attendance, duration, consolidation)
  ↓
For each recommendation: calculate estimated savings
  ↓
Return: { recommendations: [{ category, suggestion, estimated_savings }] }
  ↓
Frontend renders recommendations as read-only text + savings
```

## Components and Interfaces

### 1. Frontend Component

**File Structure:**
```
frontend/
├── index.html       (Form layout, input fields, results display)
├── css/
│   └── style.css    (Responsive design, mobile-friendly layout)
└── js/
    └── app.js       (Form logic, API integration, result rendering)
```

**Key Responsibilities:**
- Collect meeting details: subject, duration (minutes), attendees with seniority levels
- Validate inputs client-side (no empty subject, valid duration, at least 1 attendee)
- Call `/calculate-cost` endpoint and display total cost prominently
- Call `/get-recommendations` endpoint and display recommendations with savings
- Show loading indicators during API calls
- Display user-friendly error messages on API failures

**Form Fields:**
- Meeting Subject: text input, required, max 200 characters
- Meeting Duration: numeric input, 15–240 minutes, 15-minute increments, defaults to 60
- Attendee List: dynamic table with Add/Remove buttons
  - Attendee Name: text input
  - Role/Job Title: text input, required, max 100 characters (e.g., "Backend Developer") — gives the AI_Recommender context beyond seniority alone
  - Seniority Level: dropdown (junior, mid-level, senior, executive), option labels show the default $/hr rate
  - Hourly Rate: numeric input, auto-filled with the seniority's default rate when seniority is selected, editable to override per attendee

**API Integration (JavaScript):**
```javascript
// Calculate cost
POST /calculate-cost
Request body: {
  subject: string,
  duration_minutes: number,
  attendees: [{ name: string, role: string, seniority: string, hourly_rate?: number }]
}

Response body: {
  total_cost: number,
  breakdown: [
    { attendee_name, role, seniority, hourly_rate, cost_contribution }
  ]
}

// Get recommendations
POST /get-recommendations
Request body: {
  subject: string,
  duration_minutes: number,
  attendees: [{ name: string, role: string, seniority: string, hourly_rate?: number }],
  total_cost: number
}

Response body: {
  recommendations: [
    {
      category: string,  // "partial_attendance" | "duration_reduction" | "consolidation"
      suggestion: string,
      estimated_savings: number
    }
  ]
}
```

**Important:** the frontend must call the API Gateway URL returned as a stack output after deployment (`ApiEndpoint`), not a hardcoded URL — this value only exists after `sam deploy` runs.

### 2. Cost Calculator Lambda

**File:** `backend/functions/calculate_cost/handler.py`

**Responsibilities:**
- Parse incoming meeting data
- Validate attendee seniority levels against allowed values
- Apply hourly rates based on seniority
- Calculate individual and total meeting costs
- Return structured cost breakdown

**Function Signature:**
```python
def lambda_handler(event, context):
    """
    Calculate meeting cost from attendee list and duration.

    Args:
        event: {
            "body": {
                "subject": str,
                "duration_minutes": int,
                "attendees": [{"name": str, "role": str, "seniority": str, "hourly_rate": float (optional)}]
            }
        }

    Returns: {
        "statusCode": 200,
        "body": {
            "total_cost": float,
            "breakdown": [
                {"attendee_name": str, "role": str, "seniority": str, "hourly_rate": float, "cost_contribution": float}
            ]
        }
    }
    """
```

**Hourly Rate Configuration (from environment):**
```
RATE_JUNIOR: 50
RATE_MID_LEVEL: 100
RATE_SENIOR: 200
RATE_EXECUTIVE: 400
```

**Algorithm:**
```
1. Parse request body (subject, duration_minutes, attendees array)
2. Validate duration_minutes is between 15 and 240
3. Validate attendees list is not empty
4. For each attendee:
   a. Validate role is non-empty and ≤100 characters
   b. If hourly_rate is provided, validate it's a positive number; else fall
      back to the default rate for that seniority level (resolve_hourly_rate)
   c. Convert duration_minutes to hours (decimal)
   d. Calculate cost = hourly_rate × duration_hours
   e. Add to breakdown array (including role, for context — it doesn't affect the calculation)
5. Sum all individual costs to get total_cost
6. Return { total_cost, breakdown }
```

**Error Handling:**
- Invalid seniority level → HTTP 400, message: "Invalid seniority level"
- Empty attendees list → HTTP 400, message: "At least one attendee required"
- Invalid duration → HTTP 400, message: "Duration must be 15–240 minutes"
- Missing/too-long role → HTTP 400, message: "attendee N role is required" / "... must be 100 characters or fewer"
- Invalid custom hourly_rate (not a positive number) → HTTP 400, message: "attendee N hourly_rate must be a positive number"
- Any exception → HTTP 500, message: "Cost calculation failed"

**Note:** this function does NOT call Bedrock and does NOT need Bedrock permissions in its execution role.

### 3. AI Recommender Lambda

**File:** `backend/functions/get_recommendations/handler.py`

**Responsibilities:**
- Construct a prompt with meeting context
- Call Amazon Bedrock Converse API with Claude Haiku 4.5
- Parse Claude's response to extract recommendations
- Calculate estimated savings for each recommendation
- Provide graceful fallback if Claude response is malformed

**Function Signature:**
```python
def lambda_handler(event, context):
    """
    Generate AI-powered cost reduction recommendations via Bedrock.

    Args:
        event: {
            "body": {
                "subject": str,
                "duration_minutes": int,
                "total_cost": float,
                "attendees": [{"name": str, "role": str, "seniority": str, "hourly_rate": float (optional)}]
            }
        }

    Returns: {
        "statusCode": 200,
        "body": {
            "recommendations": [
                {
                    "category": str,  # "partial_attendance" | "duration_reduction" | "consolidation"
                    "suggestion": str,
                    "estimated_savings": float
                }
            ]
        }
    }
    """
```

**Configuration (from environment):**
```
BEDROCK_MODEL_ID: us.anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_REGION: us-east-1
MAX_TOKENS: 500
```
Note the `us.` prefix: Claude Haiku 4.5 on Bedrock only supports invocation through a
cross-region inference profile, not the bare foundation-model ID — confirmed by testing
directly (the bare ID fails with "on-demand throughput isn't supported"). The IAM policy
below grants `bedrock:InvokeModel` on both the inference-profile ARN and the underlying
foundation-model ARN (region-wildcarded), since cross-region inference can route the
call to any of several US regions.

**Prompt Template:**
```
You are a meeting cost optimization expert. Analyze the following meeting and suggest 2-4 specific ways to reduce its cost.

Each attendee is listed with their role/job title and seniority level. Use the
role to judge whether that person's expertise is actually relevant to the
meeting subject — not just their seniority cost.

Return ONLY valid JSON, no other text, in this exact format:
[{"category": "partial_attendance" | "duration_reduction" | "consolidation",
  "affected_attendee_names": [string], "duration_reduction_minutes": number,
  "reasoning": string}]

Meeting Subject: {subject}
Duration: {duration_minutes} minutes (${total_cost} total cost)
Attendees (name — role, seniority):
{attendee_list}

Generate 2-4 recommendations. Return ONLY the JSON array, nothing else.
```
*(implemented in `build_recommendation_prompt()` in `get_recommendations/handler.py`; see that file for the exact wording, including the per-category instructions)*

**Algorithm:**
```
1. Build attendee_list string from attendees array, including each attendee's role
2. Format prompt with meeting context, instructing Claude to weigh role
   relevance to the subject, not just seniority cost
3. Call Bedrock Converse API:
   - model_id: BEDROCK_MODEL_ID
   - max_tokens: MAX_TOKENS
   - prompt: formatted template, asking for JSON-only output
4. json.loads() the response text into a list of recommendation items
5. For each item, calculate estimated_savings using each affected attendee's
   effective hourly rate (their custom hourly_rate override if provided,
   else the seniority default — see resolve_hourly_rate())
6. If parsing fails or response is malformed:
   a. Return default recommendations (e.g., "Consider making junior attendees optional")
7. Return { recommendations: [...] }
```

**Error Handling:**
- Bedrock service unavailable → HTTP 503, fallback message: "Recommendations unavailable. Here's your cost breakdown."
- Malformed Claude response → Use default recommendations, HTTP 200
- Any exception → HTTP 500, message: "Recommendation generation failed"

**Note:** this is the ONLY function whose execution role needs Bedrock permissions.

### 4. Shared Backend Logic

**File:** `backend/shared/bedrock_client.py`

**Responsibilities:**
- Centralize Bedrock client initialization
- Provide a reusable method to call the Bedrock Converse API

**Key Functions:**
```python
def get_bedrock_client():
    """
    Return boto3 bedrock-runtime client with region from environment.
    """
    pass

def call_bedrock_converse(prompt, max_tokens=500, model_id=None):
    """
    Call Bedrock Converse API and return response text.

    Args:
        prompt: str, the prompt to send to Claude
        max_tokens: int, max output tokens (default 500)
        model_id: str, Bedrock model ID (default from env: BEDROCK_MODEL_ID)

    Returns:
        str: Claude's response text

    Raises:
        Exception: If Bedrock call fails or times out. The caller (handler.py)
        is responsible for catching this and returning HTTP 503 — this function
        itself does not implement retry logic, to keep MVP scope minimal.
    """
    pass
```

### 5. Infrastructure (SAM Template)

**File:** `infrastructure/template.yaml`

This uses `AWS::Serverless::Function` and `AWS::Serverless::Api` (real SAM resource types) instead of raw CloudFormation `AWS::Lambda::Function` / `AWS::ApiGateway::*`. This matters for three reasons:
- SAM automatically creates the `AWS::Lambda::Permission` needed for API Gateway to invoke each function — no manual wiring, no risk of forgetting it
- SAM automatically generates a dedicated execution role per function when you don't specify one, or lets you attach a small scoped policy per function via `Policies:` — this is how we keep Cost Calculator and AI Recommender roles separate
- CORS is a one-line property instead of manual OPTIONS method configuration

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: MeetValue - AWS Zero to Shipped Hackathon

Globals:
  Function:
    Runtime: python3.12
    Timeout: 10
    MemorySize: 128

Resources:
  # REST API with CORS enabled for all routes
  MeetValueApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: meetcost-api
      StageName: prod
      Cors:
        AllowMethods: "'POST,OPTIONS'"
        AllowHeaders: "'Content-Type'"
        AllowOrigin: "'*'"
        # For a stricter setup post-hackathon, replace '*' with the exact
        # S3 website URL once known.

  # Cost Calculator Lambda - basic execution role only, no Bedrock access
  CalculateCostFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: meetcost-calculate-cost
      CodeUri: ../backend/functions/calculate_cost/
      Handler: handler.lambda_handler
      Environment:
        Variables:
          RATE_JUNIOR: "50"
          RATE_MID_LEVEL: "100"
          RATE_SENIOR: "200"
          RATE_EXECUTIVE: "400"
      Events:
        CalculateCost:
          Type: Api
          Properties:
            RestApiId: !Ref MeetValueApi
            Path: /calculate-cost
            Method: POST

  # AI Recommender Lambda - execution role scoped to invoke ONLY the Haiku model
  GetRecommendationsFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: meetcost-get-recommendations
      CodeUri: ../backend/functions/get_recommendations/
      Handler: handler.lambda_handler
      Environment:
        Variables:
          BEDROCK_MODEL_ID: "us.anthropic.claude-haiku-4-5-20251001-v1:0"
          BEDROCK_REGION: "us-east-1"
          MAX_TOKENS: "500"
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource:
                - !Sub "arn:aws:bedrock:us-east-1:${AWS::AccountId}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
                - "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
      Events:
        GetRecommendations:
          Type: Api
          Properties:
            RestApiId: !Ref MeetValueApi
            Path: /get-recommendations
            Method: POST

  # S3 bucket for static frontend hosting
  MeetValueFrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "meetcost-frontend-${AWS::AccountId}"
      WebsiteConfiguration:
        IndexDocument: index.html
      PublicAccessBlockConfiguration:
        BlockPublicAcls: false
        BlockPublicPolicy: false
        IgnorePublicAcls: false
        RestrictPublicBuckets: false

  MeetValueBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref MeetValueFrontendBucket
      PolicyDocument:
        Statement:
          - Effect: Allow
            Principal: "*"
            Action: s3:GetObject
            Resource: !Sub "${MeetValueFrontendBucket.Arn}/*"

Outputs:
  FrontendBucketUrl:
    Description: URL of the static frontend
    Value: !GetAtt MeetValueFrontendBucket.WebsiteURL
  ApiEndpoint:
    Description: Base URL for the API - use this in frontend/js/app.js
    Value: !Sub "https://${MeetValueApi}.execute-api.${AWS::Region}.amazonaws.com/prod"
```

**What changed vs. the original draft, and why:**
- `Transform: AWS::Serverless-2016-10-31` added — required for any real SAM template; without it `sam deploy` cannot process `AWS::Serverless::*` resources
- Switched to `AWS::Serverless::Function` + `Events: Api` — this auto-generates the `AWS::Lambda::Permission` that was missing, so API Gateway is actually allowed to invoke the functions
- Switched to `AWS::Serverless::Api` with a `Cors` block — fixes the missing CORS bug that would have blocked every frontend request
- `Policies:` is defined only on `GetRecommendationsFunction` — `CalculateCostFunction` gets SAM's default minimal execution role (CloudWatch Logs only), enforcing least privilege
- Fixed Bedrock model ID to `anthropic.claude-haiku-4-5-20251001-v1:0` everywhere
- Fixed the Bedrock resource ARN to include `foundation-model/`
- Fixed `!Sub "meetcost-frontend-${AWS::AccountId}"` (was a literal, non-functional `{AccountId}` placeholder)

## Data Models

### Meeting Request (Frontend → Backend)

```typescript
interface MeetingRequest {
  subject: string;           // e.g., "Q4 Planning"
  duration_minutes: number;  // 15–240, increments of 15, defaults to 60 in the UI
  attendees: Attendee[];
}

interface Attendee {
  name: string;
  role: string;               // e.g., "Backend Developer" — job title/context for the AI_Recommender
  seniority: "junior" | "mid-level" | "senior" | "executive";
  hourly_rate?: number;       // optional override; defaults to the seniority's rate if omitted
}
```

### Cost Calculation Response

```typescript
interface CostResponse {
  total_cost: number;  // e.g., 410.00
  breakdown: CostBreakdown[];
}

interface CostBreakdown {
  attendee_name: string;
  role: string;
  seniority: string;
  hourly_rate: number;  // e.g., 50, 100, 200, 400, or the attendee's custom override
  cost_contribution: number;  // e.g., 41.67
}
```

### Recommendation Response

```typescript
interface RecommendationResponse {
  recommendations: Recommendation[];
}

interface Recommendation {
  category: "partial_attendance" | "duration_reduction" | "consolidation";
  suggestion: string;  // e.g., "Make junior attendees optional"
  estimated_savings: number;  // e.g., 50.00
}
```

### Hourly Rate Configuration

```python
HOURLY_RATES = {
    "junior": 50,
    "mid-level": 100,
    "senior": 200,
    "executive": 400
}
```

These are the *defaults*, applied when an attendee doesn't provide a custom
`hourly_rate` override. `resolve_hourly_rate(attendee)` in
`backend/shared/constants.py` is the single place both Lambdas use to decide
an attendee's effective rate (custom override if positive, else the
seniority default). The frontend shows these defaults next to each
seniority option and duplicates them in `DEFAULT_RATES` (`app.js`) to
auto-fill the rate field — see the maintenance note in both files if these
values ever change.

## Error Handling

### Lambda Error Response Format

All Lambda functions return errors in this format:

```python
{
    "statusCode": <400|500|503>,
    "body": {
        "error": "Error message",
        "details": "Optional diagnostic info"
    }
}
```

### Error Scenarios

| Scenario | Status | Message | Action |
|----------|--------|---------|--------|
| Invalid input (empty subject, invalid duration) | 400 | "Invalid request: {details}" | Frontend shows error, user corrects |
| Invalid seniority level | 400 | "Invalid seniority level: {value}" | Frontend validates before submit |
| Empty attendees list | 400 | "At least one attendee required" | Frontend requires ≥1 attendee |
| Lambda timeout (>10s) | 504 | (API Gateway error) | Frontend shows "Request timed out" |
| Bedrock service unavailable | 503 | "Recommendations unavailable. Here's your cost breakdown." | Frontend shows cost without recommendations |
| Bedrock call fails (other) | 500 | "Recommendation generation failed" | Frontend shows generic error |
| Cost calculation exception | 500 | "Cost calculation failed" | Frontend shows generic error |

### Frontend Error Handling

- Display clear, user-friendly messages for all errors
- Never show exception stack traces or AWS service names
- Provide actionable guidance (e.g., "Please check your input and try again")
- Disable submit button while request is in flight
- Show loading spinner during API calls

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: Cost Calculation Accuracy
*For any* meeting with a valid attendee list and duration, the calculated total cost SHALL equal the sum of all individual attendee costs.
**Validates: Requirements 1.3**
```
total_cost = Σ (hourly_rate[seniority] × duration_hours) for all attendees
```

### Property 2: Hourly Rate Consistency
*For any* attendee with a specific seniority level, the Cost_Calculator SHALL apply the correct hourly rate: junior=$50, mid-level=$100, senior=$200, executive=$400.
**Validates: Requirements 1.2**

### Property 3: Duration Conversion Correctness
*For any* meeting duration in minutes, the Cost_Calculator SHALL correctly convert it to decimal hours (e.g., 90 minutes = 1.5 hours).
**Validates: Requirements 8.1**
Test samples: 15 min = 0.25h, 30 min = 0.5h, 90 min = 1.5h, 240 min = 4.0h

### Property 4: Cost Breakdown Completeness
*For any* meeting with N attendees, the breakdown list SHALL contain exactly N entries.
**Validates: Requirements 1.5**
Invariant: `len(breakdown) == len(attendees)` and `Σ breakdown[i].cost_contribution == total_cost`

### Property 5: Cost Breakdown Accuracy
*For any* attendee in the breakdown, their cost contribution SHALL match hourly_rate × duration_hours.
**Validates: Requirements 1.1, 1.3**

### Property 6: Client-Side Input Validation
*For any* invalid form submission, the Frontend_Interface SHALL reject it and display an error before making an API call.
**Validates: Requirements 3.4, 6.4**

### Property 7: API Endpoint Responsiveness
*For any* valid request, the Cost_Calculator Lambda SHALL complete within 10 seconds and return the expected JSON shape.
**Validates: Requirements 5.6**

### Property 8: Cost Calculator Error Propagation
*For any* invalid input, the Lambda SHALL return HTTP 400 with a descriptive error message.
**Validates: Requirements 4.2**

### Property 9: Recommendation Parsing Robustness
*For any* Claude response (well-formed or not), the AI_Recommender SHALL either extract structured recommendations or fall back to defaults, never throwing an unhandled exception.
**Validates: Requirements 8.4**

### Property 10: Savings Calculation Accuracy
*For any* recommendation, estimated_savings SHALL equal original_total_cost − recalculated_cost_with_modification.
**Validates: Requirements 2.5**

### Property 11: AI Prompt Completeness
*For any* meeting, the prompt sent to Claude_Haiku SHALL include subject, duration, total cost, and attendee roles.
**Validates: Requirements 2.2, 8.2**

### Property 12: Bedrock Service Failure Graceful Degradation
*When* the Bedrock call fails, the Lambda SHALL return HTTP 503 with a fallback message, never a raw AWS error.
**Validates: Requirements 4.3**

### Property 13: Recommendation Response Structure
*For any* successful response, each recommendation SHALL have `category`, non-empty `suggestion`, and non-negative `estimated_savings`.
**Validates: Requirements 2.4, 2.6**

### Property 14: Frontend Cost Display Accuracy
*For any* returned cost, the Frontend_Interface SHALL display it formatted as currency, matching the backend value exactly.
**Validates: Requirements 1.4**

### Property 15: Frontend Breakdown Rendering Completeness
*For any* breakdown, all attendees SHALL be displayed, and displayed individual costs SHALL sum to the displayed total.
**Validates: Requirements 1.5**

### Property 16: Frontend Recommendation Display Accuracy
*For any* recommendations, each SHALL be displayed as read-only text with its estimated savings formatted as currency.
**Validates: Requirements 2.6**

### Property 17: Minute-to-Hour Conversion Boundary Cases
*For any* duration at the range boundaries (15, 240) or common intervals (30, 45, 60, 90, 120), conversion SHALL be mathematically correct.
**Validates: Requirements 8.1**

### Property 18: Seniority Level Validation
*For any* unrecognized seniority level, the Cost_Calculator SHALL reject with HTTP 400, never silently defaulting.
**Validates: Requirements 1.2, 4.2**

## Testing Strategy

### Unit Tests (Example-Based)

**Cost Calculator Tests:**
- Single junior attendee, 15 min → expected cost $12.50
- Mixed attendees, 1 hour → expected total cost and breakdown
- Empty attendees list → 400 error
- Invalid seniority level → 400 error
- Duration outside 15–240 range → 400 error
- Edge case: 240 minutes with executive → high cost calculation

**AI Recommender Tests:**
- Bedrock call succeeds → returns parsed recommendations with savings
- Malformed Claude response → falls back to default recommendations
- Bedrock service unavailable → returns 503 fallback message
- Environment variable loading (model ID, max tokens)

**Frontend Tests:**
- Empty subject → validation error shown
- Attendee list requires ≥1 attendee → validation error shown
- Successful cost calculation → cost headline + breakdown displayed
- Successful recommendation retrieval → recommendations + savings displayed
- API error → user-friendly message displayed
- Loading indicator appears during API call
- Add/Remove attendee buttons work
- Responsive layout on mobile (≤600px)

### Integration Tests
- End-to-end: input → cost calculated → recommendations retrieved → all displayed
- API Gateway correctly routes to each Lambda (verifies the Lambda Permission wiring)
- CORS preflight (OPTIONS) succeeds from the S3 website origin
- Bedrock unavailable → graceful fallback end-to-end

### Manual Testing Checklist
- [ ] Frontend loads from S3 without errors
- [ ] Form accepts valid meeting details
- [ ] Cost calculation displays prominently (e.g., "$410")
- [ ] Cost breakdown shows each attendee's contribution
- [ ] Recommendations display with estimated savings
- [ ] Error messages are clear and actionable
- [ ] Mobile layout is readable on phones/tablets
- [ ] Loading indicators appear during API calls
- [ ] Bedrock service failure shows fallback message
- [ ] No CORS errors in browser console

## Design Decisions and Rationale

### 1. Stateless Architecture
No persistent data store (DynamoDB); all computation is stateless. Faster to build, easier to reason about, and sufficient for a hackathon demo. Future iteration can add persistence for saved meetings.

### 2. Two Separate Lambda Functions
Cost calculation and recommendations are separate endpoints and functions, each with its own execution role. This lets the frontend show cost immediately without waiting on the (slower, AI-dependent) recommendations call, and keeps Bedrock permissions isolated to only the function that needs them.

### 3. Claude Haiku 4.5 via Bedrock Converse API
Haiku is the cheapest current Claude model on Bedrock, fitting hackathon budget constraints. The Converse API is simpler than the legacy InvokeModel API and handles message formatting automatically. `max_tokens=500` bounds cost per call.

### 4. Graceful Degradation on AI Failure
If Bedrock fails or the response is malformed, the user still sees the core value (meeting cost) even without recommendations — a failed AI call never breaks the whole app.

### 5. Client-Side Input Validation
Faster feedback, fewer unnecessary Lambda invocations. The backend still validates independently, since client-side validation is not a security boundary.

### 6. Static Frontend on S3, Real SAM Resources for Backend
No build step for the frontend — plain HTML/CSS/JS served from S3, zero compute cost. Using `AWS::Serverless::Function` / `AWS::Serverless::Api` (instead of raw CloudFormation resources) for the backend removes an entire class of deployment bugs (missing invoke permissions, missing CORS) for free.

## Deployment Notes

1. Run `sam deploy --guided` from the `infrastructure/` folder to deploy the stack (name it `meetcost-stack` when prompted)
2. Deployment outputs will include:
   - `FrontendBucketUrl` — the S3 static website URL
   - `ApiEndpoint` — the API Gateway base URL
3. Update `frontend/js/app.js` with the real `ApiEndpoint` value before uploading
4. Upload frontend files to the S3 bucket: `aws s3 sync frontend/ s3://meetcost-frontend-<your-account-id>/`
5. Open `FrontendBucketUrl` in a browser to verify the app works end-to-end

## Security Considerations

- Each Lambda has its own execution role; only AI Recommender's role includes Bedrock permissions, scoped to the exact Claude Haiku 4.5 model ARN
- No hardcoded credentials in source code; all config via environment variables
- Frontend validates inputs; backend validates independently (client-side validation is UX only, not a security control)
- API Gateway CORS is set to `*` for hackathon simplicity; tighten to the exact S3 website origin after the deadline if the project continues
- No sensitive data (meeting content, user identities) is persisted anywhere