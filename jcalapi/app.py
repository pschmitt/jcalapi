import datetime
import logging
import re
import os

from contextvars import ContextVar
from typing import Optional

import xdg

from dateutil.utils import within_delta
from dateutil.parser import parse as dparse
from dateutil.tz import tzlocal
from diskcache import Cache
from fastapi import FastAPI, HTTPException
from fastapi_utils.tasks import repeat_every

from jcalapi.backend.confluence import get_confluence_events
from jcalapi.backend.exchange import get_exchange_events

app = FastAPI()

CALENDAR_DATA = {"exchange": [], "confluence": []}
CACHE = Cache(os.path.join(xdg.xdg_cache_home(), "jcalapi"))
CACHE_KEY_META_SUFFIX = "-metadata"
CACHE_EXPIRY = 60 * 10  # 10 minutes
CACHE_RESTORED = ContextVar("CACHE_RESTORED", default=False)


LOGGER = logging.getLogger(__name__)


def events_merged():
    merged = []
    for vals in CALENDAR_DATA.values():
        merged += vals
    return merged


def cache_events(key):
    res_data = CACHE.set(key, CALENDAR_DATA[key], expire=CACHE_EXPIRY)
    # Save metdata
    meta = {"last-update": datetime.datetime.now(), "entries": len(CALENDAR_DATA[key])}
    res_meta = CACHE.set(f"{key}{CACHE_KEY_META_SUFFIX}", meta)
    return res_data, res_meta


def cache_restore():
    # Load data from cache
    # NOTE: This requires CALENDAR_DATA to be properly initialized (with all
    # the backends as keys)
    for key in CALENDAR_DATA.keys():
        cached_data = CACHE.get(key)
        if cached_data:
            CALENDAR_DATA[key] = cached_data
            LOGGER.info(f"Loaded {key} data from cache")
        else:
            LOGGER.warning(f"Cache for {key} is empty")
    LOGGER.info(f"Cached values have been restored")
    CACHE_RESTORED.set(True)


@app.on_event("startup")
@repeat_every(seconds=60 * 5)  # 5 minutes
async def startup_event():
    LOGGER.info(f"Startup event triggered -> CACHE_RESTORED={CACHE_RESTORED}")
    # At the very first start restore from cache, after that run reload()
    # at every interval
    if not CACHE_RESTORED.get():
        cache_restore()
    else:
        LOGGER.info(f"Refreshing events data")
        await reload()


@app.post("/reload")
async def reload(
    confluence_url: Optional[str] = None,
    confluence_username: Optional[str] = None,
    confluence_password: Optional[str] = None,
    exchange_username: Optional[str] = None,
    exchange_password: Optional[str] = None,
    exchange_email: Optional[str] = None,
):
    res_confluence = await reload_confluence(
        url=confluence_url, username=confluence_username, password=confluence_password
    )
    res_exchange = await reload_exchange(
        username=exchange_username,
        password=exchange_password,
        email=exchange_email,
    )
    return [res_confluence, res_exchange]


@app.post("/reload/confluence")
async def reload_confluence(
    url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    confluence_url = url if url else os.environ.get("CONFLUENCE_URL")
    confluence_username = (
        username if username else os.environ.get("CONFLUENCE_USERNAME")
    )
    confluence_password = (
        password if password else os.environ.get("CONFLUENCE_PASSWORD")
    )
    backend = "confluence"

    if confluence_url:
        LOGGER.info(f"Fetch calendar events from Confluence: {confluence_url}")
        CALENDAR_DATA[backend] = await get_confluence_events(
            url=confluence_url,
            username=confluence_username,
            password=confluence_password,
            start=None,
            end=None,
        )
        cache_events(backend)

    return {"events": len(CALENDAR_DATA.get("confluence", []))}


@app.post("/reload/exchange")
async def reload_exchange(
    email: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    exchange_email = email if email else os.environ.get("EXCHANGE_EMAIL")
    exchange_username = username if username else os.environ.get("EXCHANGE_USERNAME")
    exchange_password = password if password else os.environ.get("EXCHANGE_PASSWORD")
    backend = "exchange"

    LOGGER.info(f"Fetch calendar events from Exchange for user {exchange_username}")

    CALENDAR_DATA["exchange"] = await get_exchange_events(
        username=exchange_username,
        email=exchange_email,
        password=exchange_password,
        start=None,
        end=None,
    )

    cache_events(backend)

    return {"events": len(CALENDAR_DATA.get("exchange", []))}


@app.get("/events")
@app.get("/events/{backend}")
@app.get("/events/{backend}/{calendar}")
async def events(backend: Optional[str] = "all", calendar: Optional[str] = "all"):
    if backend and backend != "all" and backend not in CALENDAR_DATA.keys():
        raise HTTPException(status_code=404, detail=f"Unknown backend: {backend}")

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


@app.get("/today")
@app.get("/agenda/{when}")
async def get_events_at_date(when: Optional[str] = "today"):
    now = datetime.datetime.now(tz=tzlocal())
    target_date = now  # default to today ie now

    if when in ["tomorrow", "tom"]:
        target_date = now + datetime.timedelta(days=1)
    elif when in ["yesterday", "yest"]:
        target_date = now - datetime.timedelta(days=1)
    elif match := re.match(r"^([+-]?\d+)$", when):
        target_date = now + datetime.timedelta(days=int(match.group(1)))

    LOGGER.info(f"Grabbing agenda for {target_date}")

    agenda = []
    for ev in events_merged():
        LOGGER.debug(
            f"ITEM DATES {ev.get('summary')}: {ev.get('start')} ({type(ev.get('start'))}) -> {ev.get('end')} ({type(ev.get('end'))})"
        )
        ev_start = ev.get("start")
        ev_end = ev.get("end")
        if isinstance(ev_start, str):
            ev_start = dparse(ev_start)
        if isinstance(ev_end, str):
            ev_end = dparse(ev_end)
        ev_start_date = (
            ev_start.date() if isinstance(ev_start, datetime.datetime) else ev_start
        )
        ev_end_date = ev_end.date() if isinstance(ev_end, datetime.datetime) else ev_end
        LOGGER.debug(f"compare: {ev_start}/{ev_end} with {target_date}")
        LOGGER.debug(f"{ev_start_date} vs {target_date.date()}")
        if (
            ev_start_date == target_date.date() or ev_end_date == target_date.date()
        ) and ev not in agenda:
            agenda.append(ev)

    # return agenda
    # Sort by start time
    return sorted(
        agenda,
        key=lambda d: d["start"]
        if isinstance(d["start"], datetime.date)
        else dparse(d["start"]),
    )
