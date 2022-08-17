from typing import Any, Optional, Protocol, TypeVar

from tgmount.tgclient import TypeInputFileLocation

SourceItemId = int


class SourceItem(Protocol):
    id: SourceItemId
    file_reference: bytes
    access_hash: int
    size: int

    def input_location(self, file_reference: Optional[bytes]) -> TypeInputFileLocation:
        raise NotImplementedError()
