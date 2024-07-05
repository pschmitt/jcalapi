#!/usr/bin/env python

import asyncio
import datetime
import json
import logging
import os
import re
from functools import partial

import tzlocal
from gcsa.google_calendar import GoogleCalendar

from jcalapi.events import guess_conference_location

LOGGER = logging.getLogger(__name__)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--credentials",
        help="Credentials path to *.apps.googleusercontent.com.json file",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--calendar-regex",
        help="Regex to filter calendars",
        required=False,
        default="",
    )
    return parser.parse_args()


async def get_google_events(
    credentials,
    calendar_regex="",
    start=None,
    end=None,
):
    # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor
    loop = asyncio.get_running_loop()
    func = partial(
        sync_get_google_events,
        credentials=credentials,
        calendar_regex=calendar_regex,
        start=start,
        end=end,
    )
    return await loop.run_in_executor(None, func)


def sync_get_google_events(
    credentials,
    calendar_regex="",
    start=None,
    end=None,
):
    gcal = GoogleCalendar(credentials_path=credentials, read_only=True)
    calendars = [
        x
        for x in gcal.get_calendar_list()
        if re.search(calendar_regex, x.summary_override or x.summary)
    ]

    calendar_names = [x.summary_override or x.summary for x in calendars]

    LOGGER.info(f"Matched calendars: {calendar_names}")

    local_tz = tzlocal.get_localzone()
    local_tz_name = tzlocal.get_localzone_name()

    today = datetime.datetime.today()
    # tomorrow = today + datetime.timedelta(days=1)
    midnight_today = datetime.datetime.combine(
        today if not start else start,
        datetime.datetime.min.time(),
        tzinfo=local_tz,
    )
    # midnight_tomorrow = datetime.datetime.combine(
    #     tomorrow if not end else end,
    #     datetime.datetime.min.time(),
    #     tzinfo=account.default_timezone,
    # )

    if not start:
        today = midnight_today  # datetime.date.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        start = last_monday
    # For end, default to start + 14 days
    if not end:
        FUTURE_DAYS_IMPORT = int(os.environ.get("FUTURE_DAYS_IMPORT", 14))
        end = start + datetime.timedelta(days=FUTURE_DAYS_IMPORT)

    data = []
    for cal in calendars:
        calendar_name = cal.summary_override or cal.summary
        calendar_id = cal.calendar_id
        LOGGER.info(f"Processing calendar {calendar_name} ({calendar_id})")
        LOGGER.info(f"Start: {start}, End: {end}")
        for ev in gcal.get_events(
            calendar_id=calendar_id,
            time_min=start,
            time_max=end,
            order_by="startTime",
            single_events=True,  # expand recurring events
            timezone=local_tz_name,
        ):
            whole_day = False

            # Convert to datetime if start/end props are date objects
            ev_start = ev.start
            if isinstance(ev_start, datetime.date) and not isinstance(
                ev_start, datetime.datetime
            ):
                ev_start = datetime.datetime.combine(
                    ev_start, datetime.time.min
                ).astimezone(local_tz)
                whole_day = True
            else:
                ev_start = ev_start.astimezone(local_tz)

            ev_end = ev.end
            if isinstance(ev_end, datetime.date) and not isinstance(
                ev_end, datetime.datetime
            ):
                ev_end = datetime.datetime.combine(
                    ev_end, datetime.time.min
                ).astimezone(local_tz)
                whole_day = True
            else:
                ev_end = ev_end.astimezone(local_tz)

            location = guess_conference_location(
                {
                    "location": ev.location,
                    "description": ev.description,
                    "extra": ev.other,
                }
            )

            ev_data = {
                "uid": ev.event_id,
                "backend": "google",
                "calendar": calendar_name,
                "organizer": (
                    ev.organizer.display_name if ev.organizer else None
                ),
                "attendees": ev.attendees,
                "summary": ev.summary,
                "description": (
                    None if ev.description == "\n" else ev.description
                ),
                "location": location,
                "start": ev_start,
                "end": ev_end,
                "whole_day": whole_day,
                "is_recurring": ev.is_recurring_instance,
                "status": ev.other.get("status"),
                "categories": None,  # TODO
                "extra": {
                    "conference_solution": ev.conference_solution,
                    "link": ev.other.get("htmlLink"),
                },
            }
            data.append(ev_data)

    return data


async def async_main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    data = await get_google_events(
        credentials=args.credentials,
        calendar_regex=args.calendar_regex,
        start=None,
        end=None,
    )
    print(json.dumps(data, default=str))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    coroutine = async_main()
    loop.run_until_complete(coroutine)
