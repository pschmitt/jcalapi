#!/usr/bin/env python

import asyncio
import datetime
import os
import json
import logging
from functools import partial

from bs4 import BeautifulSoup
from exchangelib import (
    DELEGATE,
    Account,
    Configuration,
    Credentials,
    EWSDate,
    EWSTimeZone,
)
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
    username,
    password,
    email=None,
    shared_inboxes=[],
    autodiscovery=True,
    service_endpoint=None,
    auth_type="NTLM",
    version=None,
    start=None,
    end=None,
):
    # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor
    loop = asyncio.get_running_loop()
    func = partial(
        sync_get_exchange_events,
        username=username,
        password=password,
        email=email,
        shared_inboxes=shared_inboxes,
        autodiscovery=autodiscovery,
        service_endpoint=service_endpoint,
        auth_type=auth_type,
        version=version,
        start=start,
        end=end,
    )
    return await loop.run_in_executor(None, func)


def sync_get_exchange_events(
    username,
    password,
    email=None,
    shared_inboxes=[],
    autodiscovery=True,
    service_endpoint=None,
    auth_type="NTLM",
    version=None,
    start=None,
    end=None,
):
    email = email if email else username
    credentials = Credentials(username, password)
    if autodiscovery:
        account = Account(email, credentials=credentials, autodiscover=True)
    else:
        config = Configuration(
            service_endpoint=service_endpoint,
            credentials=credentials,
            auth_type=auth_type,
            version=version,
            # FIXME Version should ideally be passed in a string, which we then
            # need to parse and convert to Version/Build objects
            # Example:
            # version=Version(Build(15, 1, 2507, 16), "Exchange2016"),
        )
        account = Account(
            primary_smtp_address=email, config=config, access_type=DELEGATE
        )
    # FIXME Below used to work in earlier versions of exchangelib, but now it
    # yeilds
    # ErrorAccessDenied: Access is denied. Check credentials and try again.,
    # Non-system logon cannot access System folder.
    # calendars = [
    #     x for x in account.calendar.children if isinstance(x, Calendar)
    # ] + [account.calendar]
    calendars = [account.calendar]

    shared_calendars = {}
    for shared_inbox in shared_inboxes:
        if not shared_inbox:
            # Skip if empty
            continue
        try:
            shared_calendar = SingleFolderQuerySet(
                account=account,
                folder=DistinguishedFolderId(
                    id=Calendar.DISTINGUISHED_FOLDER_ID,
                    mailbox=Mailbox(email_address=shared_inbox),
                ),
            ).resolve()
            shared_calendars[shared_calendar] = shared_inbox
            calendars.append(shared_calendar)
        except ValueError as e:
            LOGGER.warning(f"Could not find calendar for {shared_inbox}: {e}")

    today = datetime.datetime.today()
    # tomorrow = today + datetime.timedelta(days=1)
    midnight_today = datetime.datetime.combine(
        today if not start else start,
        datetime.datetime.min.time(),
        tzinfo=account.default_timezone,
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
    events = []
    for cal in calendars:
        if cal in shared_calendars:
            cal_name = f"{cal.name} ({shared_calendars[cal]})"
        else:
            cal_name = f"{cal.name} ({username})"

        LOGGER.info(f"Processing calendar {cal_name}")
        # for ev in cal.all().filter(start__range=(start, end)):
        for ev in cal.view(start, end):
            events.append(ev)

            whole_day = False
            if isinstance(ev.start, EWSDate):
                whole_day = True
                # Raw date objects
                # ev_start = ev.start
                # ev_end = ev.end
                # Convert EWSDate objects to datetime
                # ev_start = datetime.fromisoformat(ev.start.isoformat())
                # ev_end = datetime.fromisoformat(ev.end.isoformat())
                # Convert EWSDate to tz aware datetime objects
                ev_start = datetime.datetime.combine(
                    ev.start,
                    datetime.datetime.min.time(),
                    tzinfo=EWSTimeZone.localzone(),
                )
                ev_start = ev_start.replace(microsecond=0)
                ev_end = datetime.datetime.combine(
                    ev.end,
                    datetime.datetime.max.time(),
                    tzinfo=EWSTimeZone.localzone(),
                )
                ev_end = ev_end.replace(microsecond=0)
            else:
                # datetime object -> convert to local timezone
                ev_start = ev.start.astimezone(EWSTimeZone.localzone())
                ev_end = ev.end.astimezone(EWSTimeZone.localzone())

            soup = BeautifulSoup(ev.body if ev.body else "", features="lxml")
            ev_body = soup.get_text().strip() if ev.body else ""
            ms_teams_urls = [
                x.get("href")
                for x in soup.find_all("a")
                if "/meetup-join" in x.get("href", "")
            ]
            ms_teams_url = ms_teams_urls[0] if len(ms_teams_urls) > 0 else None
            location = (
                ms_teams_url
                if (
                    not ev.location
                    or ev.location.startswith("Microsoft Teams")
                )
                else ev.location
            )

            ev_status = "cancelled" if ev.is_cancelled else "confirmed"

            ev_attendees = []
            ev_optional_attendees = (
                ev.optional_attendees if ev.optional_attendees else []
            )
            ev_required_attendees = (
                ev.required_attendees if ev.required_attendees else []
            )
            for attendee_list in [
                ev_required_attendees,
                ev_optional_attendees,
            ]:
                for attendee in attendee_list:
                    ev_attendees.append(
                        {
                            "name": attendee.mailbox.name,
                            "email": attendee.mailbox.email_address,
                            "optional": attendee in ev_optional_attendees,
                            "response": attendee.response_type,
                        }
                    )

            ev_data = {
                "uid": ev.uid,
                "backend": "exchange",
                "calendar": cal_name,
                "organizer": ev.organizer.name,
                "attendees": ev_attendees,
                "summary": ev.subject,
                "description": ev_body,
                "body": ev.body,
                "location": location,
                "start": ev_start,
                "end": ev_end,
                "whole_day": whole_day,
                "is_recurring": ev.is_recurring,
                "status": ev_status,
                "categories": ev.categories,
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
