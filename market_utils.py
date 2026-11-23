from datetime import datetime, time
from zoneinfo import ZoneInfo

#using NY time zone because of US stock market, like Nasdaq
NY_TZ = ZoneInfo("America/New_York")

holidays = {
    #remainder of 2026
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",

    #coming holidays 2027
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Birthday of Martin Luther King Jr.",
    "2027-02-15": "Washington's Birthday",
    "2027-05-31": "Memorial Day",
    "2027-06-19": "Juneteenth National Independence Day",
    "2027-07-04": "Independence Day",
    "2027-09-05": "Labor Day",
    "2027-10-10": "Columbus Day",
    "2027-11-11": "Veterans Day",
    "2027-11-26": "Thanksgiving Day",
    "2027-12-25": "Christmas Day"
}

def get_market_status(open_hour, close_hour, force_open=False):
    now_ny = datetime.now(NY_TZ)
    current_date_str = now_ny.strftime("%Y-%m-%d")
    is_open = False #this is the default
    reason = "Closed"

    #before anything, check if the current day is listed holiday
    if current_date_str in holidays:
        reason = "Closed for Federal Holiday"
    elif force_open:
            is_open = True
            reason = "Force Open by Admin"
    #then check it it's a weekend
    elif now_ny.weekday() >= 5:
        reason = "Closed for weekend"
    else:
        #then check the day's hours
        current_time_float = now_ny.hour + (now_ny.minute / 60.0)
        if open_hour <= current_time_float < close_hour:
            is_open = True
            reason = "Open"
        else:
            reason = "Closed for outside trading hours"
    ny_time_display = now_ny.strftime("%I:%M %p")

    #now for the open and closed times being displayed
    open_time_display = f"{int(open_hour):02d}:{int((open_hour % 1) * 60):02d}"
    close_time_display = f"{int(close_hour):02d}:{int((close_hour % 1) * 60):02d}"

    return {
        "ny_time": ny_time_display,
        "is_open": is_open,
        "reason": reason,
        "open_time": open_time_display,
        "close_time": close_time_display,
        "open_hour": open_hour,
        "close_hour": close_hour
    }