from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any, Optional, Protocol, TypeGuard, TypeVar, Union

import telethon


Message = telethon.tl.custom.Message
Document = telethon.types.Document
Photo = telethon.types.Photo
TypeMessagesFilter = telethon.types.TypeMessagesFilter
TypeInputFileLocation = telethon.types.TypeInputFileLocation
InputDocumentFileLocation = telethon.types.InputDocumentFileLocation
InputPhotoFileLocation = telethon.types.InputPhotoFileLocation

DocId = int

T = TypeVar("T")


class TotalListTyped(list[T]):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    total: int


class MessageWithDocument(telethon.tl.custom.Message):
    class MessageMediaDocumentX(telethon.tl.types.MessageMediaDocument):
        document: telethon.tl.types.Document

    media: MessageMediaDocumentX

    @staticmethod
    async def guard_async(m) -> TypeGuard["MessageWithDocument"]:
        return MessageWithDocument.guard(m)

    @staticmethod
    def guard(
        msg: telethon.tl.custom.Message,
    ) -> TypeGuard["MessageWithDocument"]:

        if not isinstance(msg, telethon.tl.custom.Message):
            return False

        if not hasattr(msg, "media"):
            return False

        if not hasattr(msg.media, "document"):
            return False

        # XXX
        if isinstance(msg.media.document, telethon.types.DocumentEmpty):  # type: ignore
            return False

        return True


class MessageWithPhoto(telethon.tl.custom.Message):
    class MessageMediaPhotoX(telethon.tl.types.MessageMediaPhoto):
        photo: telethon.tl.types.Photo

    media: MessageMediaPhotoX

    @staticmethod
    async def guard_async(m) -> TypeGuard["MessageWithPhoto"]:
        return MessageWithDocument.guard(m)

    @staticmethod
    def guard(
        msg: telethon.tl.custom.Message,
    ) -> TypeGuard["MessageWithPhoto"]:

        # if not isinstance(msg, telethon.tl.custom.Message):
        #     return False

        if not hasattr(msg, "media"):
            return False

        if not isinstance(msg.media, telethon.types.MessageMediaPhoto):
            return False

        if not hasattr(msg.media, "photo"):
            return False

        if not isinstance(msg.media.photo, telethon.types.Photo):
            return False

        return True
