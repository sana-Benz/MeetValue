#!/usr/bin/env bash
# Captures read-only AWS evidence that the coding agent's credentials reach the
# MeetValue account and that the stack it deployed is live.
#
# Safe to publish: no command here can return a secret key or session token,
# the access key ID is never written (only whether one is configured), the IAM
# unique user ID is redacted, and the usage-plan API key (public anyway, it
# ships to the browser) is masked in the manifest.
#
# Usage (from the repo root):  AGENT="Kiro" bash hackathon-evidence/capture-evidence.sh
set -uo pipefail

AGENT="${AGENT:-unspecified}"
REGION="us-east-1"
STACK="meetcost-stack"
API_URL="https://zlxv6jurt6.execute-api.us-east-1.amazonaws.com/prod"
APP_URL="http://meetcost-frontend-022076688911.s3-website-us-east-1.amazonaws.com/"
OUT="$(cd "$(dirname "$0")" && pwd)"
CAPTURED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

declare -a MANIFEST=()
API_KEY=""

# run <file> <description> <command...>
run() {
  local file="$1" desc="$2"; shift 2
  "$@" > "$OUT/$file" 2>&1
  local code=$?
  MANIFEST+=("$(jq -n --arg f "$file" --arg d "$desc" --arg c "${*//$API_KEY/<api-key>}" --argjson e "$code" \
    '{file:$f, command:$c, proves:$d, exit_code:$e}')")
  echo "[$code] $file"
}

run 01-aws-cli-version.txt "CLI used by the agent" \
  aws --version

run 02-sts-get-caller-identity.json "Credentials are valid; AWS STS identifies the caller" \
  bash -c "aws sts get-caller-identity --output json | jq '.UserId = \"<redacted>\"'"

run 03-credentials-configured.json "A credential source and region are configured (key ID not recorded)" \
  bash -c "aws configure list --profile \"\${AWS_PROFILE:-default}\" >/dev/null && jq -n --arg r \"\$(aws configure get region)\" '{credentials_configured:true, access_key_id:\"<not recorded>\", region:\$r}'"

run 04-cloudformation-stack.json "The stack exists, its status, creation time and public outputs" \
  aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    --query 'Stacks[0].{StackName:StackName,Status:StackStatus,Created:CreationTime,LastUpdated:LastUpdatedTime,Outputs:Outputs}' --output json

run 05-cloudformation-deploy-history.json "Every create/update of the stack, with timestamps" \
  aws cloudformation describe-stack-events --stack-name "$STACK" --region "$REGION" \
    --query 'StackEvents[?ResourceType==`AWS::CloudFormation::Stack`].{Timestamp:Timestamp,Status:ResourceStatus}' --output json

run 06-cloudformation-resources.json "Resources the stack provisioned" \
  aws cloudformation list-stack-resources --stack-name "$STACK" --region "$REGION" \
    --query 'StackResourceSummaries[].{LogicalId:LogicalResourceId,Type:ResourceType,Status:ResourceStatus}' --output json

run 07-lambda-functions.json "The two deployed Lambda functions" \
  bash -c "for f in meetcost-calculate-cost meetcost-get-recommendations; do aws lambda get-function-configuration --function-name \$f --region $REGION --query '{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout,LastModified:LastModified,ModelId:Environment.Variables.BEDROCK_MODEL_ID}' --output json; done | jq -s ."

# The API key is read from the gitignored frontend/js/config.js at runtime so it
# is never written into this script or the evidence files.
API_KEY="$(grep -oP "RECOMMENDATIONS_API_KEY: '\K[^']+" "$OUT/../frontend/js/config.js")"
run 08-live-bedrock-recommendation.json "A real end-to-end call: API Gateway -> Lambda -> Bedrock (Claude Haiku 4.5)" \
  curl -s -X POST "$API_URL/get-recommendations" -H "Content-Type: application/json" -H "x-api-key: $API_KEY" \
    -d '{"subject":"Q4 sales pipeline review","duration_minutes":60,"attendees":[{"name":"Alice","role":"VP Sales","seniority":"executive","hourly_rate":400},{"name":"Bob","role":"Backend Developer","seniority":"junior","hourly_rate":50},{"name":"Carol","role":"Account Executive","seniority":"senior","hourly_rate":200}],"total_cost":650}'

run 09-api-usage-plan.json "Daily quota + throttle capping Bedrock spend (no key values)" \
  aws apigateway get-usage-plans --region "$REGION" \
    --query 'items[?name==`meetcost-recommendations-plan`].{Name:name,Quota:quota,Throttle:throttle}' --output json

run 10-live-app-check.txt "The public URL answers" \
  curl -s -o /dev/null -w "GET $APP_URL -> HTTP %{http_code} in %{time_total}s\n" "$APP_URL"

printf '%s\n' "${MANIFEST[@]}" | jq -s \
  --arg agent "$AGENT" --arg at "$CAPTURED_AT" --arg region "$REGION" \
  '{captured_at:$at, captured_by_agent:$agent, region:$region, commands:.}' \
  > "$OUT/00-manifest.json"
echo "Wrote $OUT/00-manifest.json"
