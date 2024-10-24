import datetime
import logging
import os
import re
from contextvars import ContextVar
from typing import List, Optional

import tzlocal
import xdg
from dateutil.parser import parse as dparse
from diskcache import Cache
from fastapi import FastAPI, HTTPException, Query
from fastapi_utils.tasks import repeat_every

import jcalapi.utils as utils
from jcalapi.backend.confluence import get_confluence_events
from jcalapi.backend.exchange import get_exchange_events
from jcalapi.backend.google import get_google_events

app = FastAPI()

CALENDAR_DATA = {"confluence": [], "exchange": [], "google": []}
CACHE = Cache(os.path.join(xdg.xdg_cache_home(), "jcalapi"))
CACHE_KEY_META_SUFFIX = "-metadata"
CACHE_EXPIRY = 60 * 10  # 10 minutes
CACHE_RESTORED = ContextVar("CACHE_RESTORED", default=False)

PAST_DAYS_IMPORT = int(os.environ.get("PAST_DAYS_IMPORT", 0))
FUTURE_DAYS_IMPORT = int(os.environ.get("FUTURE_DAYS_IMPORT", 14))
START_DATE = (
    (
        datetime.datetime.now(tz=tzlocal.get_localzone()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        - datetime.timedelta(days=PAST_DAYS_IMPORT)
    )
    if PAST_DAYS_IMPORT > 0
    else None
)
END_DATE = datetime.datetime.now(tz=tzlocal.get_localzone()).replace(
    hour=0, minute=0, second=0, microsecond=0
) + datetime.timedelta(days=FUTURE_DAYS_IMPORT)

LOGGER = logging.getLogger(__name__)


def events_merged(ignore_calendars: Optional[List[str]] = None):
    merged = []
    for vals in CALENDAR_DATA.values():
        values = (
            [x for x in vals if x.get("calendar") not in ignore_calendars]
            if ignore_calendars
            else vals
        )
        merged += values
    return merged


def cache_events(key):
    res_data = CACHE.set(key, CALENDAR_DATA[key], expire=CACHE_EXPIRY)
    # Save metadata
    meta = {
        "last-update": datetime.datetime.now(),
        "entries": len(CALENDAR_DATA[key]),
    }
    res_meta = CACHE.set(f"{key}{CACHE_KEY_META_SUFFIX}", meta)
    return res_data, res_meta


async def cache_restore():
    # Load data from cache
    # NOTE: This requires CALENDAR_DATA to be properly initialized (with all
    # the backends as keys)
    for key in CALENDAR_DATA.keys():
        cached_data = CACHE.get(key)
        if cached_data:
            CALENDAR_DATA[key] = cached_data
            LOGGER.info(f"Loaded {key} data from cache")
        else:
            LOGGER.warning(f"Cache for {key} is empty. Requesting refresh")
            if key == "exchange":
                await reload_exchange()
            elif key == "confluence":
                await reload_confluence()
            elif key == "google":
                await reload_google()

    LOGGER.info("Cached values have been restored")
    CACHE_RESTORED.set(True)


@app.on_event("startup")
@repeat_every(seconds=60 * 5)  # 5 minutes
async def startup_event():
    cache_restored = CACHE_RESTORED.get(False)
    LOGGER.info(f"Startup event triggered -> CACHE_RESTORED={cache_restored}")
    # At the very first start restore from cache, after that run reload()
    # at every interval
    if not cache_restored:
        await cache_restore()
    else:
        LOGGER.info("Refreshing events data")
        await reload()


@app.post("/reload")
async def reload(
    confluence_url: Optional[str] = None,
    confluence_username: Optional[str] = None,
    confluence_password: Optional[str] = None,
    exchange_username: Optional[str] = None,
    exchange_password: Optional[str] = None,
    exchange_email: Optional[str] = None,
    exchange_shared_inboxes: Optional[list] = [],
    google_credentials: Optional[str] = None,
    google_calendar_regex: Optional[str] = None,
):
    res_google = await reload_google(
        credentials=google_credentials,
        calendar_regex=google_calendar_regex,
    )
    res_confluence = await reload_confluence(
        url=confluence_url,
        username=confluence_username,
        password=confluence_password,
    )
    res_exchange = await reload_exchange(
        username=exchange_username,
        password=exchange_password,
        email=exchange_email,
        shared_inboxes=exchange_shared_inboxes,
    )
    return {
        "exchange": res_exchange,
        "confluence": res_confluence,
        "google": res_google,
    }


@app.post("/reload/confluence")
async def reload_confluence(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    convert_email: Optional[bool] = False,
):
    confluence_url = url if url else os.environ.get("CONFLUENCE_URL")
    confluence_username = (
        username if username else os.environ.get("CONFLUENCE_USERNAME")
    )
    confluence_password = (
        password if password else os.environ.get("CONFLUENCE_PASSWORD")
    )
    convert_email = (
        convert_email
        if convert_email
        else os.environ.get("CONFLUENCE_CONVERT_EMAIL", "false")
        in ["true", "yes", "1"]
    )
    backend = "confluence"

    if (
        not confluence_url
        or not confluence_username
        or not confluence_password
    ):
        LOGGER.warning(
            "Confluence URL, username and password are required to fetch events"
        )
        return {"events": None}

    if confluence_url:
        LOGGER.info(f"Fetch calendar events from Confluence: {confluence_url}")
        if START_DATE is not None or END_DATE is not None:
            LOGGER.info(
                f"Collecting events - Start={START_DATE}, End={END_DATE}"
            )
        CALENDAR_DATA[backend] = await get_confluence_events(
            url=confluence_url,
            username=confluence_username,
            password=confluence_password,
            convert_email=convert_email,
            start=START_DATE,
            end=END_DATE,
        )
        cache_events(backend)

    return {"events": len(CALENDAR_DATA.get(backend, []))}


@app.post("/reload/exchange")
async def reload_exchange(
    email: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    shared_inboxes: Optional[list] = [],
    autodiscovery: Optional[bool] = True,
    service_endpoint: Optional[str] = None,
    auth_type: Optional[str] = None,
    version: Optional[str] = None,
):
    exchange_email = email if email else os.environ.get("EXCHANGE_EMAIL")
    exchange_username = (
        username if username else os.environ.get("EXCHANGE_USERNAME")
    )
    exchange_password = (
        password if password else os.environ.get("EXCHANGE_PASSWORD")
    )
    exchange_autodiscovery = (
        autodiscovery
        if autodiscovery
        else os.environ.get("EXCHANGE_AUTODISCOVERY", "true").lower()
        in ["true", "yes", "1", "enable"]
    )
    exchange_service_endpoint = (
        service_endpoint
        if service_endpoint
        else os.environ.get("EXCHANGE_SERVICE_ENDPOINT")
    )
    exchange_auth_type = (
        auth_type if auth_type else os.environ.get("EXCHANGE_AUTH_TYPE")
    )
    exchange_version = (
        version if version else os.environ.get("EXCHANGE_VERSION")
    )
    exchange_shared_inboxes = (
        shared_inboxes
        if shared_inboxes
        else [
            x.strip()
            for x in os.environ.get("EXCHANGE_SHARED_INBOXES", "").split(",")
        ]
    )

    backend = "exchange"

    if not exchange_username or not exchange_password:
        LOGGER.warning(
            "Exchange username and password are required to fetch events"
        )
        return {"events": None}

    LOGGER.info(
        f"Fetch calendar events from Exchange for user {exchange_username}"
    )
    if START_DATE is not None or END_DATE is not None:
        LOGGER.info(f"Collecting events - Start={START_DATE}, End={END_DATE}")

    CALENDAR_DATA[backend] = await get_exchange_events(
        username=exchange_username,
        email=exchange_email,
        password=exchange_password,
        shared_inboxes=exchange_shared_inboxes,
        autodiscovery=exchange_autodiscovery,
        service_endpoint=exchange_service_endpoint,
        version=exchange_version,
        auth_type=exchange_auth_type,
        start=START_DATE,
        end=END_DATE,
    )

    cache_events(backend)

    return {"events": len(CALENDAR_DATA.get(backend, []))}


@app.post("/reload/google")
async def reload_google(
    credentials: Optional[str] = None,
    calendar_regex: Optional[str] = None,
):
    google_credentials = (
        credentials if credentials else os.environ.get("GOOGLE_CREDENTIALS")
    )
    google_calendar_regex = (
        calendar_regex
        if calendar_regex
        else os.environ.get("GOOGLE_CALENDAR_REGEX")
    )

    backend = "google"

    if not google_credentials:
        LOGGER.warning("Google credentials are required to fetch events")
        return {"events": None}

    LOGGER.info("Fetching calendar events from google")
    if START_DATE is not None or END_DATE is not None:
        LOGGER.info(f"Collecting events - Start={START_DATE}, End={END_DATE}")
    CALENDAR_DATA[backend] = await get_google_events(
        credentials=google_credentials,
        calendar_regex=google_calendar_regex,
        start=START_DATE,
        end=END_DATE,
    )
    cache_events(backend)

    return {"events": len(CALENDAR_DATA.get(backend, []))}


@app.get("/events")
@app.get("/events/{backend}")
@app.get("/events/{backend}/{calendar}")
async def events(
    backend: Optional[str] = "all", calendar: Optional[str] = "all"
):
    if backend and backend != "all" and backend not in CALENDAR_DATA.keys():
        raise HTTPException(
            status_code=404, detail=f"Unknown backend: {backend}"
        )

    res = (
        CALENDAR_DATA.get(backend, [])
        if (backend and backend != "all")
        else events_merged()
    )
    if calendar and calendar != "all":
        LOGGER.info(f"Filtering events by calendar name: {calendar}")
        res = [x for x in res if x.get("calendar") == calendar]
    return res


@app.get("/meta")
@app.get("/meta/{backend}")
async def get_metadata(backend: Optional[str] = "all"):
    # Single backend
    if backend and backend != "all":
        return CACHE.get(f"{backend}{CACHE_KEY_META_SUFFIX}")
    # All backends
    meta = {}
    for key in CALENDAR_DATA.keys():
        meta[key] = CACHE.get(f"{key}{CACHE_KEY_META_SUFFIX}")
    return meta


@app.get("/now")
async def get_current_events(
    ignore_calendars: Optional[List[str]] = Query(None),
):
    agenda = await get_events_at_date(
        "today", ignore_calendars=ignore_calendars
    )
    now = datetime.datetime.now(tz=tzlocal.get_localzone())
    current_events = []
    for ev in agenda:
        ev_start = ev.get("start")
        ev_end = ev.get("end")
        if isinstance(ev_start, str):
            ev_start = dparse(ev_start)
        if isinstance(ev_end, str):
            ev_end = dparse(ev_end)
        if ev_start < now < ev_end:
            LOGGER.info(f"Event {ev} is happening NOW")
            current_events.append(ev)
    return current_events


@app.get("/today")
@app.get("/today/{hours_prior}")
async def get_todays_agenda(
    ignore_calendars: Optional[List[str]] = Query(None), hours_prior: int = 0
):
    agenda = await get_events_at_date(
        "today", ignore_calendars=ignore_calendars
    )
    now = datetime.datetime.now(tz=tzlocal.get_localzone())
    # now = datetime.datetime.now()
    target_date = now + datetime.timedelta(hours=hours_prior)
    LOGGER.info(f"Get agenda for today's events - {hours_prior} hour")
    current_agenda = []
    for event in agenda:
        ev_end = event.get("end")
        if isinstance(ev_end, str):
            ev_end = dparse(ev_end)
        # Whole day events
        if not isinstance(ev_end, datetime.datetime):
            current_agenda.append(event)
        else:
            if not ev_end.tzinfo:
                ev_end = ev_end.replace(tzinfo=tzlocal.get_localzone())
            if ev_end >= target_date:
                current_agenda.append(event)
    return current_agenda


@app.get("/tom")
@app.get("/tomorrow")
async def get_tomorrows_agenda(
    ignore_calendars: Optional[List[str]] = Query(None),
):
    return await get_events_at_date(
        when="tomorrow", ignore_calendars=ignore_calendars
    )


@app.get("/agenda/{when}")
async def get_events_at_date(
    when: Optional[str] = "today",
    ignore_calendars: Optional[List[str]] = Query(None),
):
    now = datetime.datetime.now(tz=tzlocal.get_localzone())
    target_date = now  # default to today ie now

    if when in ["tomorrow", "tom"]:
        target_date = now + datetime.timedelta(days=1)
    elif when in ["yesterday", "yest"]:
        target_date = now - datetime.timedelta(days=1)
    elif when in ["monday", "mon"]:
        target_date = utils.next_monday()
    elif match := re.match(r"^([+-]?\d+)$", when):
        target_date = now + datetime.timedelta(days=int(match.group(1)))

    LOGGER.info(f"Grabbing agenda for {target_date}")

    agenda = []

    for ev in events_merged(ignore_calendars):
        LOGGER.debug(
            f"ITEM DATES {ev.get('summary')}: {ev.get('start')} ({type(ev.get('start'))}) -> {ev.get('end')} ({type(ev.get('end'))})"  # noqa: E501
        )
        ev_start = ev.get("start")
        ev_end = ev.get("end")
        if isinstance(ev_start, str):
            ev_start = dparse(ev_start)
        if isinstance(ev_end, str):
            ev_end = dparse(ev_end)
        ev_start_date = (
            ev_start.date()
            if isinstance(ev_start, datetime.datetime)
            else ev_start
        )
        ev_end_date = (
            ev_end.date() if isinstance(ev_end, datetime.datetime) else ev_end
        )
        LOGGER.debug(f"compare: {ev_start}/{ev_end} with {target_date}")
        LOGGER.debug(f"{ev_start_date} vs {target_date.date()}")
        if (
            ev_start_date == target_date.date()
            or ev_end_date == target_date.date()
        ):
            # FIXME Won't this prevent events that occur multiple times
            # in a day from being included more than once?
            if ev.get("uid") in [x.get("uid") for x in agenda]:
                LOGGER.warning(f"Duplicate event skipped: {ev}")
                continue
            agenda.append(ev)

    # remove duplicate entries from agenda
    # agenda = [dict(t) for t in {tuple(d.items()) for d in agenda}]

    # Sort by start time
    return agenda
    # return sorted(
    #     agenda,
    #     key=lambda d: d["start"]
    #     if isinstance(d["start"], datetime.date)
    #     else dparse(d["start"]),
    # )
