from telethon.events.common import EventBuilder, EventCommon
from telethon.tl.types import UpdateMessageReactions


class MessageReactionEvent(EventBuilder):
    def __init__(self, chats=None, *, blacklist_chats=False):
        super().__init__(chats, blacklist_chats=False, func=None)

    @classmethod
    def build(cls, update, others=None, self_id=None):
        if isinstance(update, UpdateMessageReactions):
            return cls.Event(update)

    class Event(EventCommon):
        # msg_id: int
        def __init__(self, update: UpdateMessageReactions):
            super().__init__(update.peer, update.msg_id, False)
            self.msg_id = update.msg_id
            self.reactions = update.reactions
