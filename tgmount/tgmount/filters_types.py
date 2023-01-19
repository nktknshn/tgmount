from abc import abstractmethod
from typing import TypeVar, Protocol, Optional, Iterable, Callable

from telethon.tl.custom import Message
from tgmount.tgclient.message_types import MessageProto

from tgmount.tgmount.file_factory import FileFactoryBase, ClassifierBase

T = TypeVar("T")
FilterConfigValue = str | dict[str, dict] | list[str | dict[str, dict]]


class FilterFromConfigContext(Protocol):
    file_factory: FileFactoryBase
    classifier: ClassifierBase


class InstanceFromConfigProto(Protocol[T]):
    @staticmethod
    @abstractmethod
    def from_config(*args) -> Optional[T]:
        ...


class FilterFromConfigProto(InstanceFromConfigProto["FilterAllMessagesProto"]):
    @staticmethod
    @abstractmethod
    def from_config(*args) -> Optional["FilterAllMessagesProto"]:
        ...


class FilterAllMessagesProto(Protocol):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def filter(self, messages: Iterable[MessageProto]) -> list[MessageProto]:
        ...

    @staticmethod
    @abstractmethod
    def from_config(*args) -> "FilterAllMessagesProto":
        ...


FilterSingleMessage = Callable[[Message], T | None | bool]
FilterAllMessages = FilterAllMessagesProto
Filter = FilterAllMessages | FilterSingleMessage
ParseFilter = Callable[[FilterConfigValue], list[Filter]]
