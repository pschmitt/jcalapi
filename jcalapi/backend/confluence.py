#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import datetime

import asynccli
import httpx
import icalendar
import recurring_ical_events
import requests

from atlassian import Confluence
from dateutil.parser import parse as dparse
from dateutil.tz import gettz

# from ics import Calendar

LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-D", "--debug", action="store_true", default=False, help="Debug logging"
    )
    parser.add_argument("-U", "--url", required=True, help="Confluence URL")
    parser.add_argument("-u", "--username", required=True, help="Username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument("-s", "--start", required=False, help="Start time")
    parser.add_argument("-e", "--end", required=False, help="End time")
    return parser.parse_args()


async def get_confluence_events(url, username, password, start=None, end=None):
    confluence_client = Confluence(url, username=username, password=password)
    cal_metadata = []
    for c in confluence_client.team_calendars_get_sub_calendars().get("payload"):
        cal = c.get("subCalendar")
        cal_id = cal.get("id")
        cal_name = cal.get("name")
        cal_tz = cal.get("timeZoneId")
        ics_url = f"{url}/rest/calendar-services/1.0/calendar/export/subcalendar/{cal_id}.ics?os_authType=basic&isSubscribe=true"
        LOGGER.info(f"{cal_name} (ID: {cal_id}): {ics_url}")
        cal_metadata.append(
            {"id": cal_id, "name": cal_name, "tz": cal_tz, "url": ics_url}
        )

    # If start is undefined, set it to next monday
    if not start:
        today = datetime.date.today()
        monday = today + datetime.timedelta(days=-today.weekday(), weeks=1)
        start = monday
    # For end, default to start + 7 days
    if not end:
        end = start + datetime.timedelta(days=7)
    LOGGER.info(f"Searching for events between {start} and {end}")

    events = []
    # ics_raw = requests.get(ics_url, auth=(args.username, args.password)).text
    async with httpx.AsyncClient() as client:
        for cal in cal_metadata:
            response = await client.get(cal["url"], auth=(username, password))
            LOGGER.debug(f"Fetch {cal['name']} - http response: {response}")

            ical = icalendar.Calendar.from_ical(response.text)
            normal_events = []

            # Get list of normal, non-recurring events
            for item in ical.walk():
                # Skip non-events
                if item.name != "VEVENT":
                    LOGGER.debug(f"Not an event ({item.name}). Skip this ical item.")
                    continue
                # TODO only add if in between start and end dates
                normal_events.append(item)

            # Recurring events
            recurring_events = recurring_ical_events.of(ical).between(start, end)

            for e in normal_events + recurring_events:
                ev_summary = (
                    e.decoded("SUMMARY").decode("utf-8").strip()
                    if "SUMMARY" in e
                    else None
                )
                ev_start = e.decoded("DTSTART")
                ev_end = e.decoded("DTEND")

                # Parse date strings if the resulting object are strings
                if isinstance(ev_start, str):
                    ev_start = dparse(ev_start)
                if isinstance(ev_end, str):
                    ev_end = dparse(ev_end)
                # Convert date to datetime
                if not isinstance(ev_start, datetime.datetime):
                    ev_start = datetime.datetime.combine(
                        ev_start, datetime.datetime.min.time(), tzinfo=gettz(cal["tz"])
                    )
                if not isinstance(ev_end, datetime.datetime):
                    ev_end = datetime.datetime.combine(
                        ev_end, datetime.datetime.min.time(), tzinfo=gettz(cal["tz"])
                    )
                ev_rrule = e.decoded("RRULE") if "RRULE" in e else None
                if ev_rrule:
                    LOGGER.info(
                        f"Recurring event: {ev_summary} [{ev_start} - {ev_end}]"
                        f"RRULE: {ev_rrule}. SKIP: Processing later."
                    )
                    continue
                ev_uid = str(e.get("UID"))
                ev_description = (
                    e.decoded("DESCRIPTION").decode("utf-8")
                    if "DESCRIPTION" in e
                    else ""
                )
                ev_location = e.decoded("LOCATION") if "LOCATION" in e else None
                ev_status = (
                    e.decoded("STATUS").decode("utf-8").lower()
                    if "STATUS" in e
                    else "confirmed"
                )

                LOGGER.debug(f"Processing: {ev_summary} [{ev_start} - {ev_end}]")
                if not isinstance(ev_start, datetime.datetime):
                    start = datetime.datetime.combine(start, datetime.time(0, 0))
                if not isinstance(ev_end, datetime.datetime):
                    end = datetime.datetime.combine(end, datetime.time(23, 59))

                # Save data
                events.append(
                    {
                        "uid": ev_uid,
                        "backend": "confluence",
                        "calendar": cal["name"],
                        "summary": ev_summary,
                        "description": ev_description,
                        "location": ev_location,
                        "start": ev_start,
                        "end": ev_end,
                        "status": ev_status,
                    }
                )

    return events


async def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    await get_confluence_events(
        args.url, args.username, args.password, args.start, args.end
    )


if __name__ == "__main__":
    app = asynccli.App(main)
    app.run()
