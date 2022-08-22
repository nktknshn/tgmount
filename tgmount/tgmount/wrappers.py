from typing import Mapping, Type

from .types import (
    DirWrapperProviderProto,
    TgmountError,
    DirWrapperConstructor,
    DirWrapper,
)


class DirWrappersProviderBase(DirWrapperProviderProto):
    wrappers: Mapping[str, DirWrapperConstructor]

    def __init__(self) -> None:
        super().__init__()

    def get_wrappers(self) -> Mapping[str, DirWrapperConstructor]:
        return self.wrappers

    async def get_wrappers_factory(self, wrapper_type: str) -> DirWrapperConstructor:
        cache = self.get_wrappers().get(wrapper_type)

        if cache is None:
            raise TgmountError(f"Missing wrapper with type: {wrapper_type}")

        return cache
