#!/usr/bin/env python
# coding: utf-8

# https://pawamoy.github.io/posts/unify-logging-for-a-gunicorn-uvicorn-app/

import logging
import sys

from environs import Env
from loguru import logger
from uvicorn import Config, Server

env = Env()
DEBUG = env.bool("DEBUG", False)
LOG_LEVEL = logging.getLevelName(env("LOG_LEVEL", "INFO"))
JSON_LOGS = env.bool("JSON_LOGS", False)
WORKERS = env.int("WORKERS", 2)
HOST = env("HOST", "127.0.0.1")
PORT = env.int("PORT", 7042)
RELOAD = env("RELOAD", DEBUG)


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


def main():
    server = Server(
        Config(
            "jcalapi.app:app",
            host=HOST,
            port=PORT,
            log_level=LOG_LEVEL,
            reload=RELOAD,
            reload_includes=["*.py"],
            workers=WORKERS,
        ),
    )

    # setup logging last, to make sure no library overwrites it
    # (they shouldn't, but it happens)
    setup_logging()

    LOGGER = logging.getLogger(__name__)
    LOGGER.info(f"Starting server on {HOST}:{PORT} with {WORKERS} workers")

    server.run()


if __name__ == "__main__":
    main()
