import asyncio
import logging
import sys

TRACE = 5
logging.addLevelName(TRACE, "TRACE")

import logging


class TgmountLogger(logging.Logger):
    def __init__(self, name: str, level=logging.NOTSET) -> None:
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)


logging.setLoggerClass(TgmountLogger)

tgmount_logger = logging.getLogger("tgmount")


def getLogger(name: str) -> TgmountLogger:
    return tgmount_logger.getChild(name)  # type: ignore


class ContextFilter(logging.Filter):
    def filter(self, record):
        try:
            asyncio.get_running_loop()
            record.task_name = asyncio.current_task().get_name()
        except (RuntimeError, AttributeError):
            record.task_name = "outside the loop"

        return True


def init_logging(debug_level: int = 0, debugs=[]):
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

    # if debug_level:
    #     handler.setLevel(debug_level)
    #     root_logger.setLevel(debug_level)
    #     tgmount_logger.setLevel(debug_level)
    #     # logging.getLogger("tgvfs").setLevel(logging.DEBUG)
    #     # logging.getLogger("tgmount-zip").setLevel(logging.DEBUG)
    #     # logging.getLogger("tgmount-cache").setLevel(logging.DEBUG)
    #     # # logging.getLogger("tgvfs-ops").setLevel(logging.DEBUG)
    #     # # logging.getLogger("tgvfs-ops-updates").setLevel(logging.INFO)
    #     # logging.getLogger("tgclient").setLevel(logging.DEBUG)
    #     # logging.getLogger("tgmount-cli").setLevel(logging.DEBUG)
    #     logging.getLogger("telethon").setLevel(logging.INFO)
    # else:
    #     handler.setLevel(debug_level)
    #     root_logger.setLevel(logging.INFO)
    #     tgmount_logger.setLevel(logging.ERROR)
    #     # logging.getLogger("tgvfs").setLevel(logging.INFO)
    #     # # logging.getLogger("tgvfs-ops").setLevel(logging.INFO)
    #     # # logging.getLogger("tgvfs-ops-updates").setLevel(logging.INFO)
    #     # logging.getLogger("tgmount-zip").setLevel(logging.INFO)
    #     # logging.getLogger("tgmount-cache").setLevel(logging.INFO)
    #     # logging.getLogger("tgmount-cli").setLevel(logging.INFO)
    #     # logging.getLogger("tgclient").setLevel(logging.INFO)
    #     logging.getLogger("telethon").setLevel(logging.ERROR)

    # for d in debugs:
    #     logging.getLogger(d).setLevel(logging.DEBUG)
