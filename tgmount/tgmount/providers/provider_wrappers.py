from abc import abstractmethod, abstractstaticmethod
from typing import Mapping, Protocol, Type, TypeVar

from tgmount import vfs
from ..error import TgmountError

T = TypeVar("T")


class DirContentWrapperProto(Protocol[T]):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        ...

    @abstractstaticmethod
    def from_config(*args) -> "DirContentWrapperProto":
        ...


class DirWrapperProviderProto(Protocol):
    @abstractmethod
    def get_wrappers(self) -> Mapping[str, Type[DirContentWrapperProto]]:
        pass

    @abstractmethod
    async def get_wrapper_cls(self, wrapper_type: str) -> Type[DirContentWrapperProto]:
        pass


class DirWrappersProviderBase(DirWrapperProviderProto):
    wrappers: Mapping[str, Type[DirContentWrapperProto]]

    def __init__(self) -> None:
        super().__init__()

    def get_wrappers(self) -> Mapping[str, Type[DirContentWrapperProto]]:
        return self.wrappers

    async def get_wrapper_cls(self, wrapper_type: str) -> Type[DirContentWrapperProto]:
        wrapper_cls = self.get_wrappers().get(wrapper_type)

        if wrapper_cls is None:
            raise TgmountError(f"Missing wrapper with type: {wrapper_type}")

        return wrapper_cls
