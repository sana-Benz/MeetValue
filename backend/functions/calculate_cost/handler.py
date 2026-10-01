import json
import os
import sys

# Add shared module to path (for local runs; in Lambda this is provided by
# the SharedLayer, which the runtime already mounts at /opt/python on sys.path)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from constants import VALID_SENIORITY_LEVELS, MAX_ATTENDEE_TEXT_LENGTH, resolve_hourly_rate

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def lambda_handler(event, context):
    """
    Calculate meeting cost from attendee list and duration.

    Args:
        event: {
            "body": {
                "subject": str,
                "duration_minutes": int,
                "attendees": [{"name": str, "seniority": str, "role": str, "hourly_rate": float (optional)}]
            }
        }

    Returns: {
        "statusCode": <int>,
        "body": {
            "total_cost": float,
            "breakdown": [
                {"attendee_name": str, "role": str, "seniority": str, "hourly_rate": float, "cost_contribution": float}
            ]
        } or {
            "error": str,
            "details": str
        }
    }
    """
    try:
        # Parse the request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        # Extract fields from body
        subject = body.get("subject", "").strip()
        duration_minutes = body.get("duration_minutes")
        attendees = body.get("attendees", [])

        # Validate subject
        if not subject:
            return create_error_response(
                400,
                "Invalid request: subject cannot be empty"
            )

        # Validate duration_minutes
        if duration_minutes is None:
            return create_error_response(
                400,
                "Invalid request: duration_minutes is required"
            )

        if not isinstance(duration_minutes, (int, float)):
            return create_error_response(
                400,
                "Invalid request: duration_minutes must be a number"
            )

        duration_minutes = int(duration_minutes)

        if duration_minutes < 15 or duration_minutes > 240:
            return create_error_response(
                400,
                "Invalid request: Duration must be 15–240 minutes"
            )

        # Validate attendees
        if not isinstance(attendees, list):
            return create_error_response(
                400,
                "Invalid request: attendees must be a list"
            )

        if len(attendees) == 0:
            return create_error_response(
                400,
                "Invalid request: At least one attendee required"
            )

        # Validate each attendee
        for i, attendee in enumerate(attendees):
            if not isinstance(attendee, dict):
                return create_error_response(
                    400,
                    f"Invalid request: attendee {i} must be an object"
                )

            if not attendee.get("name", "").strip():
                return create_error_response(
                    400,
                    f"Invalid request: attendee {i} name cannot be empty"
                )

            seniority = attendee.get("seniority", "").strip()
            if not seniority:
                return create_error_response(
                    400,
                    f"Invalid request: attendee {i} seniority is required"
                )

            if seniority not in VALID_SENIORITY_LEVELS:
                return create_error_response(
                    400,
                    f"Invalid seniority level: {seniority}"
                )

            role = attendee.get("role", "").strip()
            if not role:
                return create_error_response(
                    400,
                    f"Invalid request: attendee {i} role is required"
                )

            if len(role) > MAX_ATTENDEE_TEXT_LENGTH:
                return create_error_response(
                    400,
                    f"Invalid request: attendee {i} role must be {MAX_ATTENDEE_TEXT_LENGTH} characters or fewer"
                )

            custom_rate = attendee.get("hourly_rate")
            if custom_rate is not None:
                if isinstance(custom_rate, bool) or not isinstance(custom_rate, (int, float)) or custom_rate <= 0:
                    return create_error_response(
                        400,
                        f"Invalid request: attendee {i} hourly_rate must be a positive number"
                    )

        # All validation passed, proceed with cost calculation (task 2.3)
        
        # Calculate cost contribution for each attendee
        breakdown = []
        total_cost = 0.0
        
        # Convert duration from minutes to hours (decimal)
        duration_hours = duration_minutes / 60.0
        
        for attendee in attendees:
            attendee_name = attendee.get("name", "").strip()
            seniority = attendee.get("seniority", "").strip()
            role = attendee.get("role", "").strip()

            # Use the request's custom rate if valid, else the seniority default
            hourly_rate = resolve_hourly_rate(attendee)

            # Calculate cost contribution: hourly_rate × duration_hours
            cost_contribution = hourly_rate * duration_hours

            # Add to breakdown
            breakdown.append({
                "attendee_name": attendee_name,
                "role": role,
                "seniority": seniority,
                "hourly_rate": hourly_rate,
                "cost_contribution": round(cost_contribution, 2)
            })
            
            # Add to total
            total_cost += cost_contribution
        
        # Round total cost to 2 decimal places
        total_cost = round(total_cost, 2)
        
        # Prepare response
        response_body = {
            "total_cost": total_cost,
            "breakdown": breakdown
        }
        
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(response_body)
        }

    except json.JSONDecodeError:
        return create_error_response(
            400,
            "Invalid request: request body is not valid JSON"
        )
    except Exception as e:
        return create_error_response(
            500,
            "Cost calculation failed",
            str(e)
        )


def create_error_response(status_code, error_message, details=None):
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        error_message: Main error message
        details: Optional additional details

    Returns:
        Lambda proxy response with error body
    """
    body = {"error": error_message}
    if details:
        body["details"] = details

    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body)
    }
