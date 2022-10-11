from typing import Protocol


class MockedMessageProto(Protocol):
    @property
    def id(self):
        ...

    @property
    def file(self):
        ...

    @property
    def media(self):
        return None

    @property
    def photo(self):
        return None

    @property
    def audio(self):
        return None

    @property
    def action(self):
        return None

    @property
    def voice(self):
        return None

    @property
    def sticker(self):
        return None

    @property
    def video_note(self):
        return None

    @property
    def video(self):
        return None

    @property
    def gif(self):
        return None

    @property
    def document(self):
        return self._document

    async def get_sender(self):
        return self._sender

    def to_dict(self):
        return {"id": self.id, "document_id": None}
