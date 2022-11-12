import asyncio
import logging
import sys

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

import logging

_loggers: set[str] = set()
tgmount_logger = logging.getLogger("tgmount")


class TgmountLogger(logging.Logger):
    def __init__(self, name: str, level=logging.NOTSET) -> None:
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)


logging.setLoggerClass(TgmountLogger)


def get_loggers():
    return frozenset(_loggers)


def getLogger(name: str) -> TgmountLogger:
    _loggers.add(name)
    return tgmount_logger.getChild(name)  # type: ignore


class ContextFilter(logging.Filter):
    def filter(self, record):
        try:
            asyncio.get_running_loop()
            record.task_name = asyncio.current_task().get_name()
        except (RuntimeError, AttributeError):
            record.task_name = "outside the loop"

        return True


def init_logging(debug_level: int = 0):
    # print(f"init_logging: {debug}", file=sys.stderr)

    f = ContextFilter()
    # %(process)d %(threadName)s
    formatter = logging.Formatter(
        "%(task_name)s %(levelname)s [%(name)s]\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(f)

    root_logger = logging.getLogger()

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(handler)
    # logging.getLogger("asyncio").setLevel(logging.DEBUG)

    handler.setLevel(debug_level)
    root_logger.setLevel(debug_level)
    tgmount_logger.setLevel(debug_level)
    logging.getLogger("telethon").setLevel(logging.ERROR)
