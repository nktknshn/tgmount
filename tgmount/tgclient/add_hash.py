import telethon


def add_hash_to_telegram_message_class():
    """Makes the telethon.tl.custom.Message hashable in order to store them in sets"""

    def __eq__(self, o):
        return isinstance(o, telethon.tl.custom.Message) and o.id == self.id

    telethon.tl.custom.Message.__hash__ = lambda self: (
        self.id,
        # guards.MessageDownloadable.try_document_or_photo_id(self),
    ).__hash__()

    telethon.tl.custom.Message.__eq__ = __eq__
