# Requirements Document

## Introduction

MeetValue is a serverless web application for calculating the real-time cost of internal team meetings and using AI to suggest actionable ways to reduce meeting costs. The application makes the hidden cost of meetings visible before or during meeting planning, helping internal teams make better decisions about meeting attendance and duration.

This is an MVP scoped for a time-limited student hackathon (AWS Zero to Shipped). No persistence, no interactive recalculation, no retry logic — the goal is a working, deployable, demonstrable app.

## Glossary

- **MeetValue_System**: The complete web application including frontend, backend, and AI components
- **Frontend_Interface**: The user-facing HTML/CSS/JavaScript interface hosted on Amazon S3
- **Cost_Calculator**: The Lambda function responsible for calculating meeting costs based on inputs
- **AI_Recommender**: The Lambda function that uses Claude Haiku 4.5 via Amazon Bedrock to generate cost-saving recommendations
- **Meeting_Data**: Structured information about a meeting including subject, duration, and attendee details
- **Attendee**: A meeting participant with a name, role/job title, defined seniority level, and hourly rate (default from seniority, optionally overridden)
- **Seniority_Level**: Classification of attendees (junior, mid-level, senior, executive)
- **Hourly_Rate**: Cost per hour for an attendee based on their seniority level
- **Total_Meeting_Cost**: Calculated cost = sum of (attendee hourly rate × meeting duration)
- **Cost_Saving_Recommendation**: AI-generated suggestion to reduce meeting cost with an estimated savings amount
- **Claude_Haiku**: Amazon Bedrock Claude Haiku 4.5 model used for AI recommendations
- **API_Gateway**: Amazon API Gateway providing REST endpoints for frontend-backend communication

## Requirements

### Requirement 1: Meeting Cost Calculation

**User Story:** As a team member, I want to calculate the real-time cost of a proposed meeting, so that I can understand the financial impact before scheduling it.

#### Acceptance Criteria

1. WHEN a user submits meeting details (subject, duration, attendees with seniority), THE Cost_Calculator SHALL compute the total meeting cost
2. THE Cost_Calculator SHALL use configured default hourly rates for each seniority level (junior: $50, mid-level: $100, senior: $200, executive: $400), unless the user provides a valid custom hourly rate for that attendee, which SHALL take precedence
3. THE Total_Meeting_Cost SHALL be calculated as: sum of (attendee hourly rate × meeting duration in hours)
4. WHEN the calculation completes, THE Frontend_Interface SHALL display the total cost in a prominent headline format (e.g., "This meeting costs your company $410")
5. THE Frontend_Interface SHALL display a cost breakdown by attendee, showing each attendee's individual contribution to the total cost

### Requirement 2: AI-Powered Cost Reduction Recommendations

**User Story:** As a meeting organizer, I want AI-powered suggestions to reduce meeting costs, so that I can make informed decisions about attendance and duration.

#### Acceptance Criteria

1. WHEN a meeting cost calculation is completed, THE AI_Recommender SHALL generate actionable recommendations to reduce meeting costs
2. THE AI_Recommender SHALL call Claude_Haiku via Amazon Bedrock (Converse API) with meeting context (subject, duration, attendee names, roles, and seniority), instructing it to weigh each attendee's role relevance to the meeting subject, not just their seniority cost
3. THE Claude_Haiku call SHALL be limited to max_tokens = 500 to control cost
4. THE AI_Recommender SHALL parse Claude_Haiku responses to extract specific recommendations from these categories:
   - Partial attendance suggestions (specific roles that could be optional)
   - Duration reduction suggestions
   - Attendee consolidation suggestions
5. FOR EACH AI recommendation, THE AI_Recommender SHALL calculate an estimated savings amount based on modified meeting parameters
6. THE Frontend_Interface SHALL display each recommendation as text, with its estimated savings amount, as read-only output (no interactive recalculation)

### Requirement 3: User Interface and Input Collection

**User Story:** As a user, I want a simple, intuitive interface to input meeting details, so that I can quickly get cost calculations and recommendations.

#### Acceptance Criteria

1. THE Frontend_Interface SHALL provide form fields for:
   - Meeting subject (text input)
   - Meeting duration (numeric input in minutes, 15-minute increments from 15 to 240, defaulting to 60)
   - Attendee list with name, role/job title (text input), and seniority level selection (junior, mid-level, senior, executive)
   - Each seniority option SHALL display its default hourly rate, and each attendee SHALL have an editable hourly rate field (auto-filled from the seniority default, overridable per attendee)
2. THE Frontend_Interface SHALL include an "Add Attendee" button to dynamically add more attendees
3. THE Frontend_Interface SHALL include a "Calculate Cost" button that submits meeting details and triggers both cost calculation and AI recommendations
4. WHEN form validation fails, THE Frontend_Interface SHALL display a clear, specific error message
5. THE Frontend_Interface SHALL maintain a responsive design that works on both desktop and mobile browsers
6. THE Frontend_Interface SHALL display a loading indicator while waiting for the API response

### Requirement 4: API Integration and Error Handling

**User Story:** As a developer, I want reliable API communication between frontend and backend, so that users get clear results even when something goes wrong.

#### Acceptance Criteria

1. THE API_Gateway SHALL provide two REST endpoints:
   - POST /calculate-cost — triggers cost calculation
   - POST /get-recommendations — triggers AI recommendations
2. WHEN the Cost_Calculator Lambda fails, THE API_Gateway SHALL return HTTP 500 with a descriptive error message
3. WHEN the AI_Recommender Lambda fails due to a Bedrock service issue, THE API_Gateway SHALL return HTTP 503 with a simple fallback message (e.g., "Recommendations unavailable right now — here is your cost breakdown")
4. THE Frontend_Interface SHALL display a user-friendly error message when an API call fails, with no automatic retry

### Requirement 5: Cost Optimization and Constraints

**User Story:** As a hackathon participant, I want the application to stay within AWS Free Tier and low-cost boundaries, so that it remains affordable to operate and demo.

#### Acceptance Criteria

1. THE AI_Recommender SHALL use Claude_Haiku 4.5 exclusively (no larger Claude models)
2. THE AI_Recommender SHALL limit Claude_Haiku calls to max_tokens = 500 per request
3. THE MeetValue_System SHALL operate in the us-east-1 region for full Bedrock model availability
4. THE Frontend_Interface SHALL be hosted on Amazon S3 as a static website (no compute cost)
5. THE Lambda functions SHALL use 128MB memory configuration
6. THE Lambda functions SHALL define an explicit timeout (10 seconds) to prevent runaway execution and unexpected cost

### Requirement 6: Security and Configuration

**User Story:** As a security-conscious developer, I want proper security practices implemented, so that the application doesn't expose sensitive information or unnecessary risk.

#### Acceptance Criteria

1. THE Lambda functions SHALL use IAM execution roles scoped to least privilege permissions
2. THE Lambda functions SHALL never hardcode AWS credentials in source code
3. THE MeetValue_System SHALL use environment variables for configuration (Bedrock model ID, region, hourly rates)
4. THE Frontend_Interface SHALL validate all user inputs client-side before API submission
5. THE API_Gateway SHALL implement basic request validation on both endpoints
6. THE S3 bucket for Frontend_Interface SHALL have a CORS configuration restricted to allow only the required origin and methods

### Requirement 7: Deployment and Infrastructure

**User Story:** As an AWS beginner, I want a simple deployment process, so that I can deploy the application quickly and reliably for the hackathon.

#### Acceptance Criteria

1. THE MeetValue_System SHALL be defined in a single SAM template.yaml file
2. THE SAM template SHALL deploy all required resources:
   - Two Lambda functions (Cost_Calculator, AI_Recommender)
   - API Gateway with two endpoints
   - S3 bucket for static website hosting
   - Required IAM roles and policies
3. THE deployment SHALL use `sam deploy --guided` for the first deployment
4. THE SAM template SHALL prefix all resource names with "meetcost-" for easy identification
5. THE deployment process SHALL create a CloudFormation stack named "meetcost-stack"
6. AFTER successful deployment, THE Frontend_Interface URL SHALL be output to the console for easy access

### Requirement 8: Data Formatting

**User Story:** As a system component, I need to properly format meeting data and AI responses, so that cost calculations and recommendations are displayed correctly.

#### Acceptance Criteria

1. THE Cost_Calculator SHALL convert meeting duration from minutes to decimal hours (e.g., 90 minutes = 1.5 hours)
2. THE AI_Recommender SHALL format meeting context for Claude_Haiku using a structured prompt template
3. THE AI_Recommender SHALL parse Claude_Haiku responses to extract recommendation categories and specific suggestions
4. WHEN Claude_Haiku returns an unstructured or malformed response, THE AI_Recommender SHALL fall back to a small set of default, generic recommendations rather than failing the request