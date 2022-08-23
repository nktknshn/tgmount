from .search.search import TelegramSearch
from .client import TgmountTelegramClient
from .types import (
    Document,
    InputDocumentFileLocation,
    DocId,
    InputPhotoFileLocation,
    Photo,
    TypeInputFileLocation,
)
from .message_source import TelegramMessageSource
from .files_source import TelegramFilesSource
from .guards import is_downloadable, document_or_photo_id

# from .caps import Cap
