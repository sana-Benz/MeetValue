"""
Simple test script to verify the parsing logic works.
Run this locally before deploying: python test_parser.py
"""
import json
import sys
import os

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from handler import lambda_handler


def test_valid_request():
    """Test parsing a valid request"""
    event = {
        "body": json.dumps({
            "subject": "Q4 Planning",
            "duration_minutes": 60,
            "attendees": [
                {"name": "Alice", "role": "Backend Developer", "seniority": "junior"},
                {"name": "Bob", "role": "VP Engineering", "seniority": "executive"}
            ]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Valid request: {response['statusCode']}")
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["total_cost"] == 450.0
    assert len(body["breakdown"]) == 2
    assert body["breakdown"][0]["role"] == "Backend Developer"


def test_empty_subject():
    """Test that empty subject is rejected"""
    event = {
        "body": json.dumps({
            "subject": "",
            "duration_minutes": 60,
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Empty subject rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "subject" in body["error"].lower()


def test_invalid_duration_too_short():
    """Test that duration < 15 is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Quick sync",
            "duration_minutes": 10,
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Duration too short rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "240" in body["error"]  # Should mention valid range


def test_invalid_duration_too_long():
    """Test that duration > 240 is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Marathon meeting",
            "duration_minutes": 300,
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Duration too long rejected: {response['statusCode']}")
    assert response["statusCode"] == 400


def test_empty_attendees():
    """Test that empty attendees list is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": []
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Empty attendees rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "attendee" in body["error"].lower()


def test_invalid_seniority_level():
    """Test that invalid seniority level is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "director"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Invalid seniority rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "seniority" in body["error"].lower()


def test_missing_attendee_name():
    """Test that attendee without name is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": [{"name": "", "role": "Engineer", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Empty attendee name rejected: {response['statusCode']}")
    assert response["statusCode"] == 400


def test_missing_duration():
    """Test that missing duration is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Missing duration rejected: {response['statusCode']}")
    assert response["statusCode"] == 400


def test_invalid_json():
    """Test that invalid JSON is rejected"""
    event = {
        "body": "not valid json"
    }

    response = lambda_handler(event, None)
    print(f"✓ Invalid JSON rejected: {response['statusCode']}")
    assert response["statusCode"] == 400


def test_missing_role():
    """Test that attendee without a role is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": [{"name": "Alice", "role": "", "seniority": "junior"}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Missing role rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "role" in body["error"].lower()


def test_invalid_custom_rate():
    """Test that a non-positive custom hourly_rate is rejected"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": [{"name": "Alice", "role": "Engineer", "seniority": "junior", "hourly_rate": -10}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Invalid custom rate rejected: {response['statusCode']}")
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "hourly_rate" in body["error"].lower()


def test_custom_rate_overrides_default():
    """Test that a valid custom hourly_rate is used instead of the seniority default"""
    event = {
        "body": json.dumps({
            "subject": "Meeting",
            "duration_minutes": 60,
            "attendees": [{"name": "Alice", "role": "Consultant", "seniority": "junior", "hourly_rate": 250}]
        })
    }

    response = lambda_handler(event, None)
    print(f"✓ Custom rate applied: {response['statusCode']}")
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["breakdown"][0]["hourly_rate"] == 250
    assert body["total_cost"] == 250.0


if __name__ == "__main__":
    try:
        test_valid_request()
        test_empty_subject()
        test_invalid_duration_too_short()
        test_invalid_duration_too_long()
        test_empty_attendees()
        test_invalid_seniority_level()
        test_missing_attendee_name()
        test_missing_duration()
        test_invalid_json()
        test_missing_role()
        test_invalid_custom_rate()
        test_custom_rate_overrides_default()
        print("\n✅ All parsing tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
