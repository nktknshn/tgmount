from typing import TypeVar

from .types import TelegramFilesSourceProto

T = TypeVar("T")


class TelegramFilesSourceBase(TelegramFilesSourceProto[T]):
    pass
