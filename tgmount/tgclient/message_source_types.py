from abc import abstractmethod
from typing import Any, Awaitable, Callable, Generic, Protocol, TypeVar
from typing_extensions import TypeVarTuple, Unpack

from telethon import events
from telethon.tl.custom import Message


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
    async def get_messages(self) -> list[Message]:
        pass


class MessageSourceSubscribableProto(MessageSourceProto, Protocol):

    event_new_messages: SubscribableProto[list[Message]]
    event_removed_messages: SubscribableProto[list[Message]]
    event_edited_messages: SubscribableProto[list[tuple[Message, Message]]]

    @abstractmethod
    async def get_messages(self) -> list[Message]:
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


class SubscribableListener(Generic[T]):
    def __init__(self, source: SubscribableProto) -> None:
        self.source = source
        self.events: list[T] = []

    async def _append_events(self, sender, events: list[T]):
        self.events.extend(events)

    async def __aenter__(self):
        self.source.subscribe(self._append_events)

    async def __aexit__(self, type, value, traceback):
        self.source.unsubscribe(self._append_events)
