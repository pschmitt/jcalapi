# coding: utf-8

import re

# FIXME This regex may be too greedy
REGEX_ZOOM_URL = re.compile(r'(?P<url>https://[^/]*zoom.us/j/[^\s"]+)')
# FIXME This requires HTML formatting
REGEX_MS_TEAMS_URL = re.compile(
    r'(?P<url>https://teams.microsoft.com/l/meetup-join[^"\s+]+)'
)


def guess_conference_location(event):
    # Search in location and description
    fields = [str(event.get("location")), str(event.get("description"))]

    # Search in any extra field if any
    if "extra" in event:
        for val in event.get("extra").values():
            if val:
                # NOTE re.findall expects strings, so let's convert the values
                # to str.
                fields.append(str(val))

    for val in [x for x in fields if x]:
        for regex in [REGEX_ZOOM_URL, REGEX_MS_TEAMS_URL]:
            if m := re.findall(regex, val):
                # The first link wins
                return m[0]
