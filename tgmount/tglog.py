import logging
import asyncio
import sys

TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class TgmountLogger(logging.Logger):
    def __init__(self, name: str, level=logging.NOTSET) -> None:
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)


logging.setLoggerClass(TgmountLogger)


def getLogger(name: str) -> TgmountLogger:
    return logging.getLogger(name)  # type: ignore


class ContextFilter(logging.Filter):
    def filter(self, record):
        try:
            asyncio.get_running_loop()
            record.task_name = asyncio.current_task().get_name()
        except (RuntimeError, AttributeError):
            record.task_name = "outside the loop"

        return True


def init_logging(debug=False, debugs=[]):
    print(f"init_logging: {debug}", file=sys.stderr)

    f = ContextFilter()
    formatter = logging.Formatter(
        "%(task_name)s\t%(levelname)s\t[%(name)s]\t%(message)s",
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

    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
        logging.getLogger("tgvfs").setLevel(logging.DEBUG)
        logging.getLogger("tgmount-zip").setLevel(logging.DEBUG)
        logging.getLogger("tgmount-cache").setLevel(logging.DEBUG)
        logging.getLogger("tgvfs-ops").setLevel(logging.DEBUG)
        logging.getLogger("tgvfs-ops-updates").setLevel(logging.INFO)
        logging.getLogger("tgclient").setLevel(logging.DEBUG)
        logging.getLogger("tgmount-cli").setLevel(logging.DEBUG)
        logging.getLogger("telethon").setLevel(logging.INFO)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
        logging.getLogger("tgvfs").setLevel(logging.INFO)
        logging.getLogger("tgvfs-ops").setLevel(logging.INFO)
        logging.getLogger("tgvfs-ops-updates").setLevel(logging.INFO)
        logging.getLogger("tgmount-zip").setLevel(logging.INFO)
        logging.getLogger("tgmount-cache").setLevel(logging.INFO)
        logging.getLogger("tgmount-cli").setLevel(logging.INFO)
        logging.getLogger("tgclient").setLevel(logging.INFO)
        logging.getLogger("telethon").setLevel(logging.ERROR)

    # for d in debugs:
    #     logging.getLogger(d).setLevel(logging.DEBUG)
