from typing import (
    Awaitable,
    Callable,
    Iterable,
    Optional,
    Type,
    TypeGuard,
    TypeVar,
    Union,
)
import telethon
from .types import TelegramDocument, TelegramMusicFile


def get_document(message: telethon.tl.custom.Message) -> Optional[TelegramDocument]:
    if message.document is None:
        return None

    if message.file.name is None:
        return

    return TelegramDocument(
        file_name=message.file.name,
        message=message,
        document=message.document,
        document_id=message.document.id,
        file_reference=message.document.file_reference,
        access_hash=message.document.access_hash,
    )


def get_music_file(msg: telethon.tl.custom.Message) -> Optional[TelegramMusicFile]:
    if msg.document is None:
        return None

    if msg.audio is None:
        return None

    if msg.file is None:
        return None

    if msg.file.name is None:
        return

    if msg.file.duration is None:
        return

    if msg.file.mime_type is None:
        return

    return TelegramMusicFile(
        file_name=msg.file.name,
        performer=msg.file.performer,
        title=msg.file.title,
        duration=msg.file.duration,
        mime_type=msg.file.mime_type,
        message=msg,
        document_id=msg.document.id,
        document=msg.document,
        file_reference=msg.document.file_reference,
        access_hash=msg.document.access_hash,
    )


MB = 1048576
KB = 1024
BLOCK_SIZE = 128 * KB


def block(byte_idx: int, block_size=BLOCK_SIZE):
    return byte_idx // block_size


def split_range(offset: int, limit: int, block_size=BLOCK_SIZE):
    """
    Restrictions on upload.getFile and upload.getCdnFile parameters
    offset must be divisible by 4096 bytes
    limit must be divisible by 4096 bytes
    10485760 (1MB) must be divisible by limit
    offset / (1024 * 1024) == (offset + limit - 1) / (1024 * 1024)
    (file parts that are being downloaded must always be inside the same megabyte-sized fragment)
    """
    if offset % 4096 != 0:
        offset = (offset // 4096) * 4096

    if limit % 4096 != 0:
        limit = (limit // 4096 + 1) * 4096

    a = offset
    b = offset + limit

    starting_block = block(a, block_size)
    ending_block = block(b - 1, block_size)

    blocks = list(range(starting_block, ending_block + 1))

    rngs = list(map(lambda b: b * block_size, blocks))
    rngs.append(rngs[-1] + block_size)

    return rngs
