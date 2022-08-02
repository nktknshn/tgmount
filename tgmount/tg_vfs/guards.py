import logging

from tgmount.tgclient.types import MessageWithDocument, MessageWithPhoto
from tgmount.util.guards import compose_async_guards

logger = logging.getLogger("tgvfs")

guard_document_or_photo = compose_async_guards(
    MessageWithDocument.guard_async, MessageWithPhoto.guard_async
)
