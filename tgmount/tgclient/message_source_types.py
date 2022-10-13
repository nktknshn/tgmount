from abc import abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Optional,
    Protocol,
    TypeVar,
)

from telethon import events
from telethon.tl.custom import Message

from tgmount import tglog
from tgmount.tgclient.client_types import (
    TgmountTelegramClientEventProto,
    TgmountTelegramClientReaderProto,
)
from tgmount.util import none_fallback, sets_difference
from tgmount.tgmount.types import Set, MessagesSet
from .client import TgmountTelegramClient
from .logger import logger

T = TypeVar("T")
Arg = TypeVar("Arg")
Arg_co = TypeVar("Arg_co", covariant=True)

# MessagesSet = frozenset[Message] | set[Message]

Listener = Callable[
    [
        Any,
        Arg,
    ],
    Awaitable[None],
]


class SubscribableProto(Protocol[Arg_co]):
    @abstractmethod
    def subscribe(self, listener: Listener[Arg_co]):
        ...

    @abstractmethod
    def unsubscribe(self, listener: Listener[Arg_co]):
        ...


class MessageSourceProto(Protocol):
    @abstractmethod
    async def get_messages(self) -> Set[Message]:
        pass


class MessageSourceSubscribableProto(MessageSourceProto):

    event_new_messages: SubscribableProto[Set[Message]]
    event_removed_messages: SubscribableProto[Set[Message]]

    @abstractmethod
    async def get_messages(self) -> Set[Message]:
        ...


class Subscribable(SubscribableProto[Arg]):
    def __init__(self) -> None:
        self._listeners: list[Listener[Arg]] = []

    def subscribe(self, listener: Listener[Arg]):
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener[Arg]):
        self._listeners.remove(listener)

    async def notify(self, *args):
        for listener in self._listeners:
            await listener(self, *args)
