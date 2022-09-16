from abc import abstractmethod, abstractstaticmethod
from typing import Awaitable, Callable, Iterable, Mapping, Protocol, TypeVar
from tgmount import tg_vfs, vfs
from telethon.tl.custom import Message
from tgmount.tg_vfs.tree.helpers.by_forward import group_by_forward
from tgmount.tg_vfs.tree.helpers.music import music_by_performer
from tgmount.tg_vfs.tree.helpers.by_user import messages_by_user
from tgmount.tgclient.guards import *

from .filters import Filter

T = TypeVar("T")


class TreeProducerProto(Protocol[T]):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        ...

    @abstractmethod
    async def produce_tree(self, messages: Iterable[T]) -> tg_vfs.MessagesTree[T]:
        ...

    @abstractstaticmethod
    def from_config(*args) -> "TreeProducerProto":
        ...


class TreeProducerFilter(TreeProducerProto):
    def __init__(self, filters: list[Filter]) -> None:
        self._filters = filters

    async def produce_tree(self, messages: Iterable[T]) -> tg_vfs.MessagesTree[T]:
        messages = list(messages)
        for f in self._filters:
            messages = await f.filter(messages)
        return messages

    @abstractstaticmethod
    def from_config(*args) -> "TreeProducerProto":
        raise Exception(f"from_config is not supported")


class TreeProducerNoop(TreeProducerProto):
    def __init__(self) -> None:
        pass

    async def produce_tree(self, messages: Iterable[T]) -> tg_vfs.MessagesTree[T]:
        return list(messages)

    def from_config(*args) -> "TreeProducerProto":
        return TreeProducerNoop()


TreeProducer = TreeProducerProto
TreeProducerFunc = Callable[[Iterable[T]], Awaitable[tg_vfs.MessagesTree[T]]]
RootParser = Callable[[dict], TreeProducerFunc]


class TreeProducersProviderProto(Protocol):
    @abstractmethod
    def get_producers(self) -> Mapping[str, Type[TreeProducer]]:
        pass


class TreeProducersProviderBase(TreeProducersProviderProto):

    producers: Mapping[str, Type[TreeProducer]]

    def get_producers(self) -> Mapping[str, Type[TreeProducer]]:
        return self.producers


class MusicByPerformer(TreeProducerProto[MessageWithMusic]):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    async def produce_tree(
        self, messages: Iterable[MessageWithMusic]
    ) -> tg_vfs.MessagesTree[MessageWithMusic]:
        return music_by_performer(messages, minimum=self.minimum)

    @staticmethod
    def from_config(d: dict, parse_root: RootParser):
        minimum = d.get("minimum", 2)
        return MusicByPerformer(minimum=minimum)


async def noop_producer(messages: Iterable[Message]) -> list[Message]:
    return list(messages)


async def async_id(value):
    return value


class MessageBySender(TreeProducerProto[Message]):
    def __init__(self, minimum: int, sender_root: TreeProducerFunc) -> None:
        self.minimum = minimum
        self.sender_root = sender_root

    async def produce_tree(
        self, messages: Iterable[Message]
    ) -> tg_vfs.MessagesTree[Message]:

        return await messages_by_user(
            messages,
            minimum=self.minimum,
            user_dir_producer=self.sender_root,
        )

    @staticmethod
    def from_config(d: dict, parse_root: RootParser):
        minimum = d.get("minimum", 2)
        _sender_root = d.get("sender_root", None)

        if _sender_root is None:
            sender_root = async_id
        else:
            sender_root = parse_root(_sender_root)

        return MessageBySender(
            minimum=minimum,
            sender_root=sender_root,
        )


class MessageByForwardSource(TreeProducerProto[Message]):
    def __init__(self) -> None:
        pass

    async def produce_tree(
        self, messages: Iterable[Message]
    ) -> tg_vfs.MessagesTree[Message]:
        return await group_by_forward(
            [m for m in messages if MessageForwarded.guard(m)],
        )

    @staticmethod
    def from_config(d: dict, parse_root: RootParser):

        return MessageByForwardSource()
