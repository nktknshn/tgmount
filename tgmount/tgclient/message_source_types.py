from abc import abstractmethod
from typing import Any, Awaitable, Callable, Generic, Iterable, Protocol, TypeVar
from typing_extensions import TypeVarTuple, Unpack

from telethon import events

from tgmount.tgclient.message_types import MessageProto
from tgmount.tgclient.messages_collection import WithId


T = TypeVar("T")
Arg = TypeVar("Arg")
Arg_co = TypeVar("Arg_co", covariant=True)
M = TypeVar("M", bound=WithId)


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


# class MessageSourceProto(Generic[M], Protocol):
#     @abstractmethod
#     async def get_messages(self) -> list[M]:
#         pass


class MessageSourceProto(Generic[M], Protocol):

    event_new_messages: SubscribableProto[list[M]]
    event_removed_messages: SubscribableProto[list[M]]
    event_edited_messages: SubscribableProto[list[tuple[M, M]]]

    @abstractmethod
    async def get_messages(self) -> list[M]:
        ...

    @abstractmethod
    async def set_messages(self, messages: list[M], notify=True):
        pass

    @abstractmethod
    async def add_messages(self, messages: Iterable[M]):
        pass

    @abstractmethod
    async def edit_messages(self, messages: Iterable[M]):
        pass

    @abstractmethod
    async def get_by_ids(self, ids: list[int]) -> list[M] | None:
        pass

    @abstractmethod
    async def remove_messages_ids(self, removed_messages: list[int]):
        pass


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
