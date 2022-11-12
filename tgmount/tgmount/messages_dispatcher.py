from typing import Protocol

from tgmount.tgclient.client_types import TgmountTelegramClientEventProto


class MessageDispatcherProto(Protocol):
    """
    The meaning of this class is to accept and pass all the incoming messages.
    Pausing if neeeded so no messages are lost
    """

    async def add_source(self, source: TgmountTelegramClientEventProto):
        pass

    async def add_source(self, source: TgmountTelegramClientEventProto):
        pass
