# Hourly rates by seniority level (in dollars)
#
# MAINTENANCE NOTE: these defaults are duplicated in frontend/index.html
# (seniority dropdown option labels) and frontend/js/app.js (DEFAULT_RATES,
# used to auto-fill the per-attendee rate field). The frontend has no build
# step and can't import this file directly, so if you change a rate here,
# update those two frontend spots too.
HOURLY_RATES = {
    "junior": 50,
    "mid-level": 100,
    "senior": 200,
    "executive": 400,
}

# Valid seniority levels
VALID_SENIORITY_LEVELS = ["junior", "mid-level", "senior", "executive"]

# Maximum length for free-text attendee fields (name, role)
MAX_ATTENDEE_TEXT_LENGTH = 100


def resolve_hourly_rate(attendee):
    """
    Effective hourly rate for an attendee: their custom override from the
    request if present and a positive number, otherwise the default rate
    for their seniority level.
    """
    custom_rate = attendee.get("hourly_rate")
    if isinstance(custom_rate, (int, float)) and not isinstance(custom_rate, bool) and custom_rate > 0:
        return custom_rate
    return HOURLY_RATES.get(attendee.get("seniority", "").strip(), 0)
