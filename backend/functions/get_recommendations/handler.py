import json
import logging
import os
import sys

# Add shared module to path (for local runs; in Lambda this is provided by
# the SharedLayer, which the runtime already mounts at /opt/python on sys.path)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from constants import VALID_SENIORITY_LEVELS, MAX_ATTENDEE_TEXT_LENGTH, resolve_hourly_rate
from bedrock_client import call_bedrock_converse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def lambda_handler(event, context):
    """
    Generate AI-powered cost reduction recommendations via Bedrock.

    Args:
        event: {
            "body": {
                "subject": str,
                "duration_minutes": int,
                "total_cost": float,
                "attendees": [{"name": str, "seniority": str, "role": str, "hourly_rate": float (optional)}]
            }
        }

    Returns: {
        "statusCode": <int>,
        "body": {
            "recommendations": [
                {
                    "category": str,
                    "suggestion": str,
                    "estimated_savings": float
                }
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
        total_cost = body.get("total_cost")
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

        # Validate total_cost
        if total_cost is None:
            return create_error_response(
                400,
                "Invalid request: total_cost is required"
            )

        if not isinstance(total_cost, (int, float)):
            return create_error_response(
                400,
                "Invalid request: total_cost must be a number"
            )

        total_cost = float(total_cost)

        if total_cost < 0:
            return create_error_response(
                400,
                "Invalid request: total_cost cannot be negative"
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

        # All validation passed
        # Task 4.2: Build the prompt for Claude
        prompt = build_recommendation_prompt(
            subject=subject,
            duration_minutes=duration_minutes,
            total_cost=total_cost,
            attendees=attendees
        )

        # Task 4.3: Call call_bedrock_converse() with the prompt
        try:
            bedrock_response = call_bedrock_converse(prompt)
        except Exception as e:
            # Bedrock call failed - log server-side (never exposed to the
            # client, which only ever sees the generic fallback message
            # below) and return 503 with fallback message
            logger.error(f"Bedrock call failed: {type(e).__name__}: {str(e)}")
            return {
                "statusCode": 503,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "error": "Recommendations unavailable. Here's your cost breakdown."
                })
            }

        # Task 4.3: Parse the response using json.loads()
        recommendations = []
        try:
            recommendations_data = json.loads(strip_markdown_fence(bedrock_response))
        except json.JSONDecodeError:
            # JSON parsing failed - use default recommendations instead of erroring
            recommendations_data = get_default_recommendations()

        # Task 4.3: Extract recommendations from the parsed response
        if isinstance(recommendations_data, list):
            for item in recommendations_data:
                if isinstance(item, dict):
                    # Extract the fields we need
                    category = item.get("category", "").strip() if isinstance(item.get("category"), str) else ""
                    reasoning = item.get("reasoning", "").strip() if isinstance(item.get("reasoning"), str) else ""
                    affected_names = item.get("affected_attendee_names", [])
                    duration_reduction = item.get("duration_reduction_minutes", 0)

                    # Ensure types are correct
                    if not isinstance(affected_names, list):
                        affected_names = []
                    if not isinstance(duration_reduction, (int, float)):
                        duration_reduction = 0

                    # Only include items with category and reasoning
                    if category and reasoning:
                        # Task 4.4: Calculate estimated_savings for this recommendation
                        estimated_savings = calculate_estimated_savings(
                            category=category,
                            duration_minutes=duration_minutes,
                            total_cost=total_cost,
                            attendees=attendees,
                            affected_attendee_names=affected_names,
                            duration_reduction_minutes=int(duration_reduction)
                        )

                        # Task 4.5: Build response with proper structure
                        recommendations.append({
                            "category": category,
                            "suggestion": reasoning,
                            "estimated_savings": estimated_savings
                        })

        # If we couldn't extract any valid recommendations, use defaults
        if not recommendations:
            recommendations = get_default_recommendations()

        response_body = {
            "recommendations": recommendations
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
            "Recommendation generation failed",
            str(e)
        )


def calculate_estimated_savings(category, duration_minutes, total_cost, attendees, affected_attendee_names, duration_reduction_minutes):
    """
    Calculate estimated savings for a recommendation.

    Task 4.4: Implements the savings calculation logic.

    For partial_attendance and consolidation:
      - Sum of (hourly_rate × duration_hours) for each name in affected_attendee_names

    For duration_reduction:
      - (duration_reduction_minutes / 60) × sum of all attendees' hourly_rates

    Args:
        category: str, recommendation category
        duration_minutes: int, original meeting duration
        total_cost: float, original total meeting cost
        attendees: list of dict with 'name' and 'seniority'
        affected_attendee_names: list of str, names of affected attendees
        duration_reduction_minutes: int, minutes to reduce (for duration_reduction)

    Returns:
        float: Estimated savings in dollars

    **Validates: Requirements 2.5**
    """
    duration_hours = duration_minutes / 60.0

    if category == "partial_attendance" or category == "consolidation":
        # Sum up the effective hourly rates for affected attendees
        savings = 0.0
        for attendee in attendees:
            if attendee.get("name") in affected_attendee_names:
                savings += resolve_hourly_rate(attendee) * duration_hours
        return savings

    elif category == "duration_reduction":
        # (duration_reduction_minutes / 60) × sum of all attendees' hourly_rates
        reduction_hours = duration_reduction_minutes / 60.0
        total_hourly_rate = sum(resolve_hourly_rate(attendee) for attendee in attendees)
        savings = reduction_hours * total_hourly_rate
        return savings

    else:
        # Unknown category, return 0
        return 0.0


def build_recommendation_prompt(subject, duration_minutes, total_cost, attendees):
    """
    Build the prompt to send to Claude for cost reduction recommendations.

    The prompt instructs Claude to return ONLY valid JSON, no other text.

    Args:
        subject: str, meeting subject
        duration_minutes: int, meeting duration in minutes
        total_cost: float, total meeting cost
        attendees: list of dict with 'name' and 'seniority' keys

    Returns:
        str: formatted prompt for Claude

    **Validates: Requirements 2.2, 8.2**
    """
    # Build the attendee list for display, including each attendee's role
    attendee_list = "\n".join(
        f"  - {attendee['name']} — {attendee['role']} ({attendee['seniority']})"
        for attendee in attendees
    )

    prompt = f"""You are a meeting cost optimization expert. Analyze the following meeting and suggest 2-4 specific ways to reduce its cost.

Each attendee is listed with their role/job title and seniority level. Use the role to judge whether that person's expertise is actually relevant to the meeting subject — not just their seniority cost. For example, a sales rep's presence may not be needed for a technical deep-dive, and a backend developer may not be needed for a sales-strategy discussion, regardless of seniority.

Return ONLY valid JSON, no other text, in this exact format:
[{{"category": "partial_attendance" | "duration_reduction" | "consolidation", "affected_attendee_names": [string], "duration_reduction_minutes": number, "reasoning": string}}]

For each category:
- partial_attendance: List the specific attendee names who could be optional or join only part of the meeting, based on whether their role is relevant to the meeting subject. Set duration_reduction_minutes to 0.
- duration_reduction: List all attendees (meeting would run for everyone), specify by how many minutes to reduce. Set affected_attendee_names to all attendee names.
- consolidation: List the attendee names whose meeting could be combined with another. Set duration_reduction_minutes to 0.

In each item's "reasoning", explicitly mention the affected attendee's role and why it is or isn't relevant to this meeting's subject.

Meeting Details:
Subject: {subject}
Duration: {duration_minutes} minutes (${total_cost:.2f} total cost)
Attendees (name — role, seniority):
{attendee_list}

Generate 2-4 recommendations. Return ONLY the JSON array, nothing else."""

    return prompt


def strip_markdown_fence(text):
    """
    Strip a leading/trailing markdown code fence (```json ... ``` or ``` ... ```)
    from Claude's response, if present. Despite the prompt asking for JSON only,
    Claude sometimes wraps it in a code fence anyway; json.loads() can't parse
    that directly.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def get_default_recommendations():
    """
    Return a list of default recommendations to use when Claude response fails.

    These are used as a fallback when:
    - The Bedrock call fails
    - Claude's response cannot be parsed as JSON
    - Claude's response doesn't contain valid recommendation items

    Returns:
        list: Default recommendations with category, suggestion, and estimated_savings (0)

    **Task 4.6: Default recommendations return 0 savings**
    """
    return [
        {
            "category": "partial_attendance",
            "suggestion": "Consider making junior attendees optional or having them join for key sections only.",
            "estimated_savings": 0
        },
        {
            "category": "duration_reduction",
            "suggestion": "Consider shortening the meeting by 15 minutes — many meetings can be more efficient.",
            "estimated_savings": 0
        }
    ]


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
