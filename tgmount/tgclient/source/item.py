from typing import Optional, Protocol

from ..types import TypeInputFileLocation

SourceItemId = int


class FileSourceItem(Protocol):
    id: SourceItemId
    file_reference: bytes
    access_hash: int
    size: int

    def input_location(self, file_reference: Optional[bytes]) -> TypeInputFileLocation:
        raise NotImplementedError()
