from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from tgmount.tgclient import (
    Document,
    InputPhotoFileLocation,
    Photo,
    TypeInputFileLocation,
)

from telethon.tl.custom.file import File
from .item import SourceItemId, SourceItem


def get_photo_input_location(
    photo: Photo,
    type: str,
    file_reference: Optional[bytes] = None,
):
    return InputPhotoFileLocation(
        id=photo.id,
        access_hash=photo.access_hash,
        file_reference=file_reference
        if file_reference is not None
        else photo.file_reference,
        thumb_size=type,
    )


class SourceItemPhoto(SourceItem):
    id: SourceItemId
    file_reference: bytes
    access_hash: int
    size: int

    def __init__(self, photo: Photo) -> None:
        self.id = photo.id
        self.file_reference = photo.file_reference
        self.access_hash = photo.access_hash
        self.size = File(photo).size  # type: ignore
        self.photo = photo

    def _type(self):

        max_size = self.photo.sizes[0]

        for s in self.photo.sizes:
            if getattr(self.photo.sizes[0], "h", 0) < getattr(s, "h", 0):
                max_size = s

        return max_size.type

    def input_location(self, file_reference: Optional[bytes]) -> TypeInputFileLocation:
        type = self.photo.sizes
        return get_photo_input_location(
            self.photo,
            self._type(),
            file_reference,
        )