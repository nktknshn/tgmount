from abc import abstractmethod
from typing import (
    AnyStr,
    Awaitable,
    Callable,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

import telethon

DocId = int


class CachingDocumentsStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
