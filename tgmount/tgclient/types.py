from typing import TypeVar
import telethon

DocId = int
# Document = telethon.types.Document
# Photo = telethon.types.Photo
TypeMessagesFilter = telethon.types.TypeMessagesFilter
TypeInputFileLocation = telethon.types.TypeInputFileLocation
InputDocumentFileLocation = telethon.types.InputDocumentFileLocation
InputPhotoFileLocation = telethon.types.InputPhotoFileLocation


TT = TypeVar("TT")


class TotalListTyped(list[TT]):
    total: int
