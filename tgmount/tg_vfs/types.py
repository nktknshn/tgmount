from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol

import pyfuse3
import telethon
from telethon.tl.custom.file import File
from tgmount import vfs
from tgmount.tgclient import Document, Message


def photo_get_max_size(item: telethon.types.Photo) -> int:
    return File(item).size


def photo_get_max_type(item: telethon.types.Photo) -> int:
    return item.sizes


InputSourceItem = telethon.types.Photo | telethon.types.Document


@dataclass
class TelegramMusicFile:

    file_name: str
    performer: Optional[str]
    title: Optional[str]
    duration: int
    # voice: bool

    mime_type: str

    message: telethon.tl.custom.Message
    document: telethon.types.Document

    document_id: int
    file_reference: bytes
    access_hash: int


@dataclass
class TelegramDocument:
    file_name: str

    message: telethon.tl.custom.Message
    document: telethon.types.Document

    document_id: int
    file_reference: bytes
    access_hash: int
