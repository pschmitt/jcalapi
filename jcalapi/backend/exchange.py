#!/usr/bin/env python

import logging
import json
import datetime

from aioify import aioify
from exchangelib import Credentials, Account, EWSDate, EWSDateTime, EWSTimeZone
from exchangelib.folders import Calendar

from jcalapi.events import guess_conference_location


LOGGER = logging.getLogger(__name__)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", help="Email", required=False)
    parser.add_argument("-u", "--username", help="Username", required=True)
    parser.add_argument("-p", "--password", help="Password", required=True)
    return parser.parse_args()


async def get_exchange_events(username, password, email=None, start=None, end=None):
    aio_get_exchange_events = aioify(obj=sync_get_exchange_events)
    return await aio_get_exchange_events(
        username=username, password=password, email=email, start=start, end=end
    )


def sync_get_exchange_events(username, password, email=None, start=None, end=None):
    email = email if email else username
    credentials = Credentials(username, password)
    account = Account(email, credentials=credentials, autodiscover=True)
    calendars = [x for x in account.calendar.children] + [account.calendar]

    today = datetime.datetime.today()
    tomorrow = today + datetime.timedelta(days=7)
    midnight_today = datetime.datetime.combine(
        today if not start else start,
        datetime.datetime.min.time(),
        tzinfo=account.default_timezone,
    )
    midnight_tomorrow = datetime.datetime.combine(
        tomorrow if not end else end,
        datetime.datetime.min.time(),
        tzinfo=account.default_timezone,
    )

    if not start:
        today = datetime.date.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        start = last_monday
    # For end, default to start + 14 days
    if not end:
        end = start + datetime.timedelta(days=14)

    data = []
    events = []
    for cal in calendars:
        LOGGER.info(f"Processing calendar {cal}")
        for ev in cal.all().filter(start__range=(start, end)):
            events.append(ev)

            if isinstance(ev.start, EWSDate):
                ev_start = ev.start
                ev_end = ev.end
            else:
                # datetime object -> convert to local timezone
                ev_start = ev.start.astimezone(EWSTimeZone.localzone())
                ev_end = ev.end.astimezone(EWSTimeZone.localzone())

            ev_status = "cancelled" if ev.is_cancelled else "confirmed"

            ev_data = {
                "uid": ev.uid,
                "backend": "exchange",
                "calendar": cal.name,
                "summary": ev.subject,
                "description": ev.body,
                "location": ev.location,
                "start": ev_start,
                "end": ev_end,
                "status": ev_status,
                "extra": {
                    "conference_type": ev.conference_type,
                    "meeting_workspace_url": ev.meeting_workspace_url,
                    "net_show_url": ev.net_show_url,
                },
            }
            ev_data["conference_url"] = guess_conference_location(ev_data)
            data.append(ev_data)

    return data


def main():
    args = parse_args()
    data = get_exchange_events(
        username=args.username,
        password=args.password,
        email=args.email,
        start=None,
        end=None,
    )
    print(json.dumps(data))


if __name__ == "__main__":
    main()
