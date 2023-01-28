from abc import abstractmethod
from typing import Callable, Generic, Iterable, Protocol, TypeGuard, TypeVar

M = TypeVar("M")

FilterSingleMessage = Callable[[M], bool]


class FilterAllMessagesProto(Generic[M], Protocol):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def filter(self, messages: Iterable[M]) -> list[M]:
        ...

    @staticmethod
    @abstractmethod
    def from_config(*args) -> "FilterAllMessagesProto":
        ...

    @staticmethod
    def guard(
        filter: FilterSingleMessage[M] | "FilterAllMessagesProto[M]",
    ) -> TypeGuard["FilterAllMessagesProto[M]"]:
        return hasattr(filter, "filter")
