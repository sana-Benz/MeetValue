// Copy to config.js (gitignored) and fill in the values from your deployment.
//   API_BASE_URL:            the ApiEndpoint output of the CloudFormation stack
//   RECOMMENDATIONS_API_KEY: aws apigateway get-api-keys --include-values --query 'items[].value'
// The key is not a secret (the browser sends it); it only lets API Gateway
// enforce the daily quota that caps Bedrock spend. config.js is kept out of
// git so the key doesn't sit in the public repo.
window.MEETVALUE_CONFIG = {
  API_BASE_URL: 'https://{api-id}.execute-api.{region}.amazonaws.com/prod',
  RECOMMENDATIONS_API_KEY: '<your-usage-plan-api-key>',
};
