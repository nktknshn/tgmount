from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any, Optional, Protocol, TypeGuard, TypeVar, Union

import telethon

DocId = int
Message = telethon.tl.custom.Message
Document = telethon.types.Document
Photo = telethon.types.Photo
TypeMessagesFilter = telethon.types.TypeMessagesFilter
TypeInputFileLocation = telethon.types.TypeInputFileLocation
InputDocumentFileLocation = telethon.types.InputDocumentFileLocation
InputPhotoFileLocation = telethon.types.InputPhotoFileLocation
