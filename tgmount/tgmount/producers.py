from abc import abstractmethod, abstractstaticmethod
from typing import Awaitable, Callable, Iterable, Mapping, Protocol, TypeVar
from tgmount import tg_vfs, vfs
from telethon.tl.custom import Message
from tgmount.tg_vfs.tree.helpers.music import music_by_performer
from tgmount.tg_vfs.tree.helpers.by_user import messages_by_user
from tgmount.tgclient.guards import *

T = TypeVar("T")


class TreeProducerProto(Protocol[T]):
    @abstractmethod
    async def produce_tree(self, messages: Iterable[T]) -> tg_vfs.MessagesTree[T]:
        ...

    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractstaticmethod
    def from_config(*args) -> "TreeProducerProto":
        ...


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
