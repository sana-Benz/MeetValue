# MeetValue — Technical Stack

## Backend
- Language: Python 3.12
- Compute: AWS Lambda (one function per responsibility, e.g. calculate_cost, get_recommendations)
- API layer: Amazon API Gateway (REST API)
- Database: Amazon DynamoDB (single table design, simple key-value storage for meetings)
- AI: Amazon Bedrock, Claude Haiku 4.5, called via the Converse API (not the legacy InvokeModel API)

## Frontend
- Plain HTML, CSS, and vanilla JavaScript (no framework)
- Hosted on Amazon S3 as a static website (or S3 + CloudFront if time allows)
- Communicates with backend via fetch() calls to API Gateway endpoints

## Infrastructure as Code
- AWS SAM (Serverless Application Model), template.yaml
- Deployment via `sam deploy --guided`

## Region
us-east-1 (chosen for full Bedrock model availability)

## Security constraints
- No hardcoded AWS credentials anywhere in code
- Lambda functions use their own IAM execution role (least privilege, scoped to meetcost-* resources)
- Environment variables for configuration (never secrets in code)

## Cost constraints
- Claude Haiku 4.5 only (cheapest Claude model on Bedrock)
- max_tokens capped at 300–500 per Bedrock call
- No provisioned throughput, on-demand only

## Notes
- `.env` is gitignored — use it for local secrets (AWS credentials, region, model IDs)
- Do not commit credentials or `.env` files
