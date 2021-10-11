#!/usr/bin/env python

import logging
import json
from datetime import datetime, timedelta

from aioify import aioify
from exchangelib import Credentials, Account, EWSDate, EWSDateTime
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

    today = datetime.today()
    tomorrow = today + timedelta(days=7)
    midnight_today = datetime.combine(
        today if not start else start,
        datetime.min.time(),
        tzinfo=account.default_timezone,
    )
    midnight_tomorrow = datetime.combine(
        tomorrow if not end else end,
        datetime.min.time(),
        tzinfo=account.default_timezone,
    )

    data = []
    events = []
    for cal in calendars:
        LOGGER.info(f"Processing calendar {cal}")
        for ev in cal.all().filter(start__range=(midnight_today, midnight_tomorrow)):
            events.append(ev)

            # Check for whole day events
            if isinstance(ev.start, EWSDate):
                start = midnight_today
                end = midnight_tomorrow
            else:
                start = datetime.fromtimestamp(int(ev.start.timestamp()))
                end = datetime.fromtimestamp(int(ev.end.timestamp()))
            ev_data = {
                "uid": ev.uid,
                "backend": "exchange",
                "calendar": cal.name,
                "summary": ev.subject,
                "description": ev.body,
                "location": ev.location,
                "start": str(ev.start),
                "end": str(ev.end),
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
