from abc import abstractmethod
from typing import Any, Awaitable, Callable, Protocol, TypeVar
from typing_extensions import TypeVarTuple, Unpack

from telethon import events
from telethon.tl.custom import Message


from .types import Set

T = TypeVar("T")
Arg = TypeVar("Arg")
Arg_co = TypeVar("Arg_co", covariant=True)


Ts = TypeVarTuple("Ts")

Listener = Callable[
    [
        Any,
        *Ts,
    ],
    Awaitable[None],
]


class SubscribableProto(Protocol[Arg_co]):
    @abstractmethod
    def subscribe(self, listener: Listener):
        ...

    @abstractmethod
    def unsubscribe(self, listener: Listener):
        ...


class MessageSourceProto(Protocol):
    @abstractmethod
    async def get_messages(self) -> Set[Message]:
        pass


class MessageSourceSubscribableProto(MessageSourceProto, Protocol):

    event_new_messages: SubscribableProto[Set[Message]]
    event_removed_messages: SubscribableProto[Set[Message]]
    event_edited_messages: SubscribableProto[list[tuple[Message, Message]]]

    @abstractmethod
    async def get_messages(self) -> Set[Message]:
        ...


class Subscribable(SubscribableProto[Arg]):
    def __init__(self) -> None:
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener):
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener):
        self._listeners.remove(listener)

    async def notify(self, *args):
        for listener in self._listeners:
            await listener(self, *args)
