"""
Shared Bedrock client initialization and utilities.
"""

import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


def get_bedrock_client():
    """
    Return a boto3 bedrock-runtime client with region from environment.
    
    The region is read from the BEDROCK_REGION environment variable.
    If the environment variable is missing or invalid, this function
    will raise an error with a clear message.
    
    Returns:
        botocore.client.BaseClient: A boto3 bedrock-runtime client
        
    Raises:
        ValueError: If BEDROCK_REGION environment variable is not set
        ClientError: If the region is invalid or AWS credentials are missing
    """
    region = os.environ.get('BEDROCK_REGION')
    
    if not region:
        raise ValueError(
            "BEDROCK_REGION environment variable is not set. "
            "Please set it to a valid AWS region (e.g., 'us-east-1')"
        )
    
    try:
        client = boto3.client('bedrock-runtime', region_name=region)
        return client
    except NoCredentialsError as e:
        raise ValueError(
            "AWS credentials not found. Ensure AWS credentials are configured "
            "(via IAM role, environment variables, or ~/.aws/credentials)"
        ) from e
    except ClientError as e:
        raise ValueError(
            f"Failed to initialize Bedrock client with region '{region}': {str(e)}"
        ) from e


def call_bedrock_converse(prompt, max_tokens=500, model_id=None):
    """
    Call Amazon Bedrock Converse API with Claude and return the response text.
    
    Args:
        prompt (str): The prompt to send to Claude
        max_tokens (int): Maximum tokens in the response (default: 500)
        model_id (str): Bedrock model ID (default: from BEDROCK_MODEL_ID env var)
    
    Returns:
        str: The response text from Claude
    
    Raises:
        ValueError: If required environment variables are not set
        ClientError: If the Bedrock API call fails
        Exception: If the response has an unexpected structure
    """
    # Use provided model_id or get from environment
    if model_id is None:
        model_id = os.environ.get('BEDROCK_MODEL_ID')
        if not model_id:
            raise ValueError(
                "BEDROCK_MODEL_ID environment variable is not set"
            )
    
    # Get the Bedrock client
    client = get_bedrock_client()
    
    # Call the Converse API
    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": max_tokens
        }
    )
    
    # Extract the response text from the first content block
    # The Converse API returns content in a list
    try:
        response_text = response['output']['message']['content'][0]['text']
        return response_text
    except (KeyError, IndexError, TypeError) as e:
        raise Exception(
            f"Unexpected response structure from Bedrock Converse API: {str(e)}"
        ) from e
