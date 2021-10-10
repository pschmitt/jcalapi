#!/usr/bin/env python
# coding: utf-8

# https://pawamoy.github.io/posts/unify-logging-for-a-gunicorn-uvicorn-app/

import os
import logging
import sys

from uvicorn import Config, Server
from loguru import logger

LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "INFO"))
JSON_LOGS = True if os.environ.get("JSON_LOGS", "0") == "1" else False


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    # intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(LOG_LEVEL)

    # remove every other logger's handlers
    # and propagate to root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # configure loguru
    logger.configure(handlers=[{"sink": sys.stdout, "serialize": JSON_LOGS}])


if __name__ == "__main__":
    server = Server(
        Config(
            "jcalapi.app:app",
            host="127.0.0.1",
            log_level=LOG_LEVEL,
            reload=True,
            reload_includes=["*.py"]
            # debug=True,
            # workers=2,
        ),
    )

    # setup logging last, to make sure no library overwrites it
    # (they shouldn't, but it happens)
    setup_logging()

    server.run()
