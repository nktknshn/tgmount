import telethon

from . import guards


def add_hash():
    telethon.tl.custom.Message.__hash__ = lambda self: (
        self.id,
        guards.MessageDownloadable.try_document_or_photo_id(self),
    ).__hash__()
