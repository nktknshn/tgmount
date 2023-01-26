import asyncio
import logging
import sys
import tgmount
from tgmount.util import yes

TRACE = 5
logging.addLevelName(TRACE, "TRACE")


_loggers: set[str] = set()
tgmount_logger = logging.getLogger("tgmount")


def get_name_part(name: str, part_idx: int) -> str | None:
    parts = name.split(".")

    try:
        return parts[part_idx]
    except KeyError:
        return None


class TgmountLogger(logging.Logger):
    def __init__(self, name: str, level=logging.NOTSET) -> None:
        super().__init__(name, level)

        self.suffix_as_tag = False

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)

    def getChild(self, suffix: str, suffix_as_tag=False) -> "TgmountLogger":
        child = super().getChild(suffix)
        child.suffix_as_tag = suffix_as_tag
        return child

    def makeRecord(self, *args, **kwargs) -> logging.LogRecord:

        rec = super().makeRecord(*args, **kwargs)

        if self.suffix_as_tag and yes(self.parent):
            rec.name = self.parent.name
            rec.__dict__["tag"] = get_name_part(self.name, -1)
        else:
            rec.__dict__["tag"] = None

        return rec


logging.setLoggerClass(TgmountLogger)


def get_loggers():
    return frozenset(_loggers)


def getLogger(name: str) -> TgmountLogger:
    _loggers.add(name)
    return tgmount_logger.getChild(name)  # type: ignore


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        task = asyncio.current_task

        if yes(task) and hasattr(task, "get_name"):
            record.task_name = task.get_name()
        else:
            record.task_name = "outside the loop"

        return True


class TgmountLogRecord(logging.LogRecord):
    tag: str | None
    task_name: str


class Formatter(logging.Formatter):
    grey = "\x1b[90;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    white = "\x1b[38;20m"
    reset = "\x1b[0m"

    COLORS = {
        TRACE: grey,
        logging.DEBUG: grey,
        logging.INFO: white,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def __init__(self, print_task_name=False) -> None:
        self.print_task_name = print_task_name

    def _format(self, rec: TgmountLogRecord) -> str:
        rec.message = rec.getMessage()
        rec.name = rec.name.replace("tgmount.", "", 1)

        if hasattr(rec, "tag") and yes(rec.tag):
            log_str = f"{rec.levelname} [{rec.name}] [{rec.tag}] {rec.message}"
        else:
            log_str = f"{rec.levelname} [{rec.name}] {rec.message}"

        if self.print_task_name:
            log_str = f"{rec.task_name} {log_str}"

        return log_str

    def format(self, rec: TgmountLogRecord) -> str:

        if rec.levelno not in self.COLORS:
            return self._format(rec)

        color = self.COLORS[rec.levelno]

        return color + self._format(rec) + self.reset


def init_logging(debug_level: int = 0):
    # print(f"init_logging: {debug_level}", file=sys.stderr)
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    logging.getLogger("telethon").setLevel(logging.INFO)

    tgmount.tgmount.logger.setLevel(debug_level)
    tgmount.tgmount.filters.logger.setLevel(logging.INFO)
    tgmount.tgmount.producers.producer_plain.VfsTreeProducerPlainDir.logger.setLevel(
        logging.INFO
    )

    tgmount.tgmount.producers.grouperbase.VfsTreeProducerGrouperBase.logger.setLevel(
        logging.INFO
    )

    tgmount.fs.logger.setLevel(logging.INFO)

    # tgmount.tgmount.wrappers.logger.setLevel(logging.INFO)
    tgmount.tgmount.wrappers.wrapper_exclude_empty_dirs.WrapperEmpty.logger.setLevel(
        logging.INFO
    )

    handler = logging.StreamHandler()
    handler.setFormatter(Formatter())
    handler.addFilter(ContextFilter())

    root_logger = logging.getLogger()

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(handler)
    tgmount_logger.setLevel(debug_level)
