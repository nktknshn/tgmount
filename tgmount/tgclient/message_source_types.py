from abc import abstractmethod
from typing import Any, Awaitable, Callable, Protocol, TypeVar

from telethon import events
from telethon.tl.custom import Message


from tgmount.tgmount.types import Set

T = TypeVar("T")
Arg = TypeVar("Arg")
Arg_co = TypeVar("Arg_co", covariant=True)


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


class MessageSourceSubscribableProto(MessageSourceProto, Protocol):

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
