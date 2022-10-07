from typing import Any, Mapping

from telethon.tl.custom import Message


Set = frozenset
MessagesSet = Set[Message]
TgmountRootSource = Mapping
MessageTuple = tuple[int, int | None]
