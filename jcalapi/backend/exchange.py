#!/usr/bin/env python

import asyncio
import datetime
import json
import logging

from aioify import aioify
from exchangelib import Account, Credentials, EWSDate, EWSDateTime, EWSTimeZone
from exchangelib.folders import Calendar, SingleFolderQuerySet
from exchangelib.properties import DistinguishedFolderId, Mailbox

from jcalapi.events import guess_conference_location

LOGGER = logging.getLogger(__name__)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", help="Email", required=False)
    parser.add_argument("-u", "--username", help="Username", required=True)
    parser.add_argument("-p", "--password", help="Password", required=True)
    parser.add_argument(
        "-s",
        "--shared_inboxes",
        action="append",
        help="Shared Inboxes",
        required=False,
        default=[],
    )
    return parser.parse_args()


async def get_exchange_events(
    username, password, email=None, shared_inboxes=[], start=None, end=None
):
    aio_get_exchange_events = aioify(obj=sync_get_exchange_events)
    return await aio_get_exchange_events(
        username=username,
        password=password,
        email=email,
        shared_inboxes=shared_inboxes,
        start=start,
        end=end,
    )


def sync_get_exchange_events(
    username, password, email=None, shared_inboxes=[], start=None, end=None
):
    email = email if email else username
    credentials = Credentials(username, password)
    account = Account(email, credentials=credentials, autodiscover=True)
    calendars = [x for x in account.calendar.children] + [account.calendar]

    shared_calendars = {}
    for shared_inbox in shared_inboxes:
        shared_calendar = SingleFolderQuerySet(
            account=account,
            folder=DistinguishedFolderId(
                id=Calendar.DISTINGUISHED_FOLDER_ID,
                mailbox=Mailbox(email_address=shared_inbox),
            ),
        ).resolve()
        shared_calendars[shared_calendar] = shared_inbox
        calendars.append(shared_calendar)

    # today = datetime.datetime.today()
    # tomorrow = today + datetime.timedelta(days=7)
    # midnight_today = datetime.datetime.combine(
    #     today if not start else start,
    #     datetime.datetime.min.time(),
    #     tzinfo=account.default_timezone,
    # )
    # midnight_tomorrow = datetime.datetime.combine(
    #     tomorrow if not end else end,
    #     datetime.datetime.min.time(),
    #     tzinfo=account.default_timezone,
    # )

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

            if cal in shared_calendars:
                cal_name = f"{cal.name} ({shared_calendars[cal]})"
            else:
                cal_name = f"{cal.name} ({username})"

            ev_data = {
                "uid": ev.uid,
                "backend": "exchange",
                "calendar": cal_name,
                "organizer": ev.organizer.name,
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


async def async_main():
    args = parse_args()
    data = await get_exchange_events(
        username=args.username,
        password=args.password,
        email=args.email,
        shared_inboxes=args.shared_inboxes,
        start=None,
        end=None,
    )
    print(json.dumps(data, default=str))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    coroutine = async_main()
    loop.run_until_complete(coroutine)
