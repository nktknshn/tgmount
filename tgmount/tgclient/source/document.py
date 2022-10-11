from typing import Optional

from tgmount.tgclient.message_types import DocumentProto

from ..types import InputDocumentFileLocation, TypeInputFileLocation
from .item import SourceItemId, SourceItem


def get_document_input_location(
    document: DocumentProto, file_reference: Optional[bytes] = None
):
    return InputDocumentFileLocation(
        id=document.id,
        access_hash=document.access_hash,
        file_reference=file_reference
        if file_reference is not None
        else document.file_reference,
        thumb_size="",
    )


class SourceItemDocument(SourceItem):
    id: SourceItemId
    file_reference: bytes
    access_hash: int
    size: int

    def __init__(self, document: DocumentProto) -> None:
        self.id = document.id
        self.file_reference = document.file_reference
        self.access_hash = document.access_hash
        self.size = document.size
        self.document = document

    def input_location(self, file_reference: Optional[bytes]) -> TypeInputFileLocation:
        return get_document_input_location(self.document, file_reference)
