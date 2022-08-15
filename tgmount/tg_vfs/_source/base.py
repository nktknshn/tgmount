from typing import Any, Awaitable, Callable, Optional, Protocol, Generic, TypeVar

import telethon
from telethon.tl.custom import Message
from tgmount import vfs
from tgmount.tgclient.guards import (
    MessageDownloadable,
    MessageWithCompressedPhoto,
    MessageWithDocument,
)

from .types import TelegramFilesSourceProto

T = TypeVar("T")


class TelegramFilesSourceBase(TelegramFilesSourceProto[T]):
    pass
