from datetime import datetime, timedelta


def next_monday():
    today = datetime.now()
    days_ahead = (
        -today.weekday() + 7
    )  # Monday is 0, so to get to the next Monday, add 7 days
    if (
        today.weekday() == 0
    ):  # If today is Monday, we get the next Monday instead of today
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    return next_monday
