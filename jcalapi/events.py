# coding: utf-8

import re

# FIXME This regex may be too greedy
REGEX_ZOOM_URL = re.compile(r'(?P<url>https://[^/]*zoom.us/j/[^\s"]+)')
# FIXME This requires HTML formatting
REGEX_MS_TEAMS_URL = re.compile(
    r'(?P<url>https://teams.microsoft.com/l/meetup-join[^"\s+]+)'
)


def guess_conference_location(event):
    for key in ["location", "description"]:
        if val := str(event.get(key)):
            for regex in [REGEX_ZOOM_URL, REGEX_MS_TEAMS_URL]:
                if m := re.findall(regex, val):
                    # The first link wins
                    return m[0]
