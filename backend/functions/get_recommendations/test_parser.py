"""
Unit tests for get_recommendations parsing logic (task 4.1).
"""
import json
import sys
import os
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))


def test_valid_request():
    """Test that a valid request is parsed correctly."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"},
                {"name": "Bob", "role": "VP Engineering", "seniority": "executive"}
            ]
        }
    }
    
    # Mock successful Bedrock response
    mock_response = json.dumps([
        {
            "category": "partial_attendance",
            "affected_attendee_names": ["Alice"],
            "duration_reduction_minutes": 0,
            "reasoning": "Junior staff could skip this meeting."
        }
    ])
    
    with mock.patch('handler.call_bedrock_converse', return_value=mock_response):
        result = lambda_handler(event, None)
    
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)


def test_empty_subject():
    """Test that empty subject returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "error" in body
    assert "subject cannot be empty" in body["error"]


def test_missing_duration():
    """Test that missing duration_minutes returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "duration_minutes is required" in body["error"]


def test_invalid_duration_too_short():
    """Test that duration < 15 minutes returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 10,
            "total_cost": 200.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Duration must be 15–240 minutes" in body["error"]


def test_invalid_duration_too_long():
    """Test that duration > 240 minutes returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 300,
            "total_cost": 2000.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Duration must be 15–240 minutes" in body["error"]


def test_missing_total_cost():
    """Test that missing total_cost returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "total_cost is required" in body["error"]


def test_negative_total_cost():
    """Test that negative total_cost returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": -100.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "total_cost cannot be negative" in body["error"]


def test_empty_attendees():
    """Test that empty attendees list returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": []
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "At least one attendee required" in body["error"]


def test_invalid_seniority_level():
    """Test that invalid seniority level returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "invalid-level"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "Invalid seniority level" in body["error"]


def test_empty_attendee_name():
    """Test that empty attendee name returns 400 error."""
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "name cannot be empty" in body["error"]


def test_request_body_as_string():
    """Test that request body as JSON string is parsed correctly."""
    from handler import lambda_handler
    
    event = {
        "body": json.dumps({
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        })
    }
    
    mock_response = json.dumps([
        {
            "category": "duration_reduction",
            "affected_attendee_names": ["Alice"],
            "duration_reduction_minutes": 15,
            "reasoning": "Reduce meeting by 15 minutes."
        }
    ])
    
    with mock.patch('handler.call_bedrock_converse', return_value=mock_response):
        result = lambda_handler(event, None)
    
    assert result["statusCode"] == 200


def test_all_seniority_levels():
    """Test that all valid seniority levels are accepted."""
    from handler import lambda_handler
    
    for seniority in ["junior", "mid-level", "senior", "executive"]:
        event = {
            "body": {
                "subject": "Q4 Planning",
                "duration_minutes": 60,
                "total_cost": 450.0,
                "attendees": [
                    {"name": "Person", "role": "Engineer", "seniority": seniority}
                ]
            }
        }
        
        mock_response = json.dumps([
            {
                "category": "partial_attendance",
                "affected_attendee_names": ["Person"],
                "duration_reduction_minutes": 0,
                "reasoning": "This person could be optional."
            }
        ])
        
        with mock.patch('handler.call_bedrock_converse', return_value=mock_response):
            result = lambda_handler(event, None)
        
        assert result["statusCode"] == 200, f"Failed for seniority: {seniority}"


def test_bedrock_call_failure():
    """
    Test task 4.7: Bedrock call failure returns HTTP 503 with fallback message.
    
    **Validates: Task 4.7**
    
    When the call_bedrock_converse() function raises an exception,
    the handler should catch it and return a 503 error with the message:
    "Recommendations unavailable. Here's your cost breakdown."
    """
    from handler import lambda_handler
    
    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }
    
    # Mock the call_bedrock_converse to raise an exception
    with mock.patch('handler.call_bedrock_converse', side_effect=Exception("Bedrock API error")):
        result = lambda_handler(event, None)
    
    assert result["statusCode"] == 503, f"Expected 503, got {result['statusCode']}"
    body = json.loads(result["body"])
    assert "error" in body
    assert body["error"] == "Recommendations unavailable. Here's your cost breakdown."


def test_missing_role():
    """Test that an attendee without a role returns 400 error."""
    from handler import lambda_handler

    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "", "seniority": "junior"}
            ]
        }
    }

    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    body = json.loads(result["body"])
    assert "role" in body["error"].lower()


def test_prompt_includes_role():
    """Test that the built prompt mentions each attendee's role, so Claude
    can reason about role fit relative to the meeting subject."""
    from handler import build_recommendation_prompt

    prompt = build_recommendation_prompt(
        subject="Sales Strategy Review",
        duration_minutes=60,
        total_cost=450.0,
        attendees=[
            {"name": "Alice", "role": "Backend Developer", "seniority": "junior"},
            {"name": "Bob", "role": "Sales Rep", "seniority": "senior"},
        ]
    )

    assert "Backend Developer" in prompt
    assert "Sales Rep" in prompt
    assert "role" in prompt.lower()


def test_markdown_fenced_response():
    """Test that a Bedrock response wrapped in a ```json code fence still
    parses correctly, instead of falling back to default recommendations.
    Regression test: seen live in production — Claude sometimes wraps its
    JSON response in a markdown fence despite being told to return JSON only."""
    from handler import lambda_handler

    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 450.0,
            "attendees": [
                {"name": "Alice", "role": "Engineer", "seniority": "junior"}
            ]
        }
    }

    fenced_response = "```json\n" + json.dumps([
        {
            "category": "partial_attendance",
            "affected_attendee_names": ["Alice"],
            "duration_reduction_minutes": 0,
            "reasoning": "Alice's role isn't relevant to this planning session."
        }
    ]) + "\n```"

    with mock.patch('handler.call_bedrock_converse', return_value=fenced_response):
        result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    # A real recommendation should come through, not the 0-savings defaults
    assert body["recommendations"][0]["category"] == "partial_attendance"
    assert body["recommendations"][0]["estimated_savings"] == 50.0


def test_custom_rate_used_in_savings():
    """Test that a custom hourly_rate is used (instead of the seniority
    default) when calculating estimated_savings."""
    from handler import lambda_handler

    event = {
        "body": {
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "total_cost": 250.0,
            "attendees": [
                {"name": "Alice", "role": "Consultant", "seniority": "junior", "hourly_rate": 250}
            ]
        }
    }

    mock_response = json.dumps([
        {
            "category": "partial_attendance",
            "affected_attendee_names": ["Alice"],
            "duration_reduction_minutes": 0,
            "reasoning": "Alice's expertise isn't needed for this planning session."
        }
    ])

    with mock.patch('handler.call_bedrock_converse', return_value=mock_response):
        result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    # 1 hour at the $250 custom rate, not the $50 junior default
    assert body["recommendations"][0]["estimated_savings"] == 250.0


if __name__ == "__main__":
    print("Running parsing tests...")
    test_valid_request()
    print("✓ test_valid_request")
    
    test_empty_subject()
    print("✓ test_empty_subject")
    
    test_missing_duration()
    print("✓ test_missing_duration")
    
    test_invalid_duration_too_short()
    print("✓ test_invalid_duration_too_short")
    
    test_invalid_duration_too_long()
    print("✓ test_invalid_duration_too_long")
    
    test_missing_total_cost()
    print("✓ test_missing_total_cost")
    
    test_negative_total_cost()
    print("✓ test_negative_total_cost")
    
    test_empty_attendees()
    print("✓ test_empty_attendees")
    
    test_invalid_seniority_level()
    print("✓ test_invalid_seniority_level")
    
    test_empty_attendee_name()
    print("✓ test_empty_attendee_name")
    
    test_request_body_as_string()
    print("✓ test_request_body_as_string")
    
    test_all_seniority_levels()
    print("✓ test_all_seniority_levels")
    
    test_bedrock_call_failure()
    print("✓ test_bedrock_call_failure")

    test_missing_role()
    print("✓ test_missing_role")

    test_prompt_includes_role()
    print("✓ test_prompt_includes_role")

    test_custom_rate_used_in_savings()
    print("✓ test_custom_rate_used_in_savings")

    test_markdown_fenced_response()
    print("✓ test_markdown_fenced_response")

    print("\nAll parsing tests passed! ✓")
