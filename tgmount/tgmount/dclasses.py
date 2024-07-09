import mimetypes
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any, Optional

import pyfuse3
from telethon.tl.custom import Message



@dataclass
class TgmountDocument:
    chat_id: int
    message_id: int
    document_id: str
    message_date: Optional[datetime]
    document_date: datetime
    mime_type: str
    size: int

    attributes: dict


@dataclass
class DocumentHandle:
    document: TgmountDocument
    read_func: Callable


@dataclass
class TgfsFile:
    msg: Message
    handle: DocumentHandle
    inode: Optional[int]
    attr: Optional[pyfuse3.EntryAttributes]

    @property
    def fname(self):
        return message_doc_filename_format(self.msg, self.handle.document)


def message_doc_filename_format(msg: Message, doc: TgmountDocument):
    attr_file_name = doc.attributes.get('file_name')

    if attr_file_name:
        return f"{msg.id} {attr_file_name}".encode()
    else:
        ext = mimetypes.guess_extension(doc.mime_type)
        return f"{msg.id} unnamed{ext}".encode()
