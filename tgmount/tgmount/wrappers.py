from typing import Mapping, Type


from .types import (
    DirWrapperProviderProto,
    TgmountError,
    DirWrapperConstructor,
    DirWrapper,
)

from tgmount import zip as z, vfs


async def zips_as_dirs(**kwargs) -> DirWrapper:
    async def _inner(content: vfs.DirContentProto) -> vfs.DirContentProto:
        return z.zips_as_dirs(content, **kwargs)

    return _inner


class DirWrappersProvider(DirWrapperProviderProto):
    def __init__(self) -> None:
        super().__init__()

    def get_wrappers(self) -> Mapping[str, DirWrapperConstructor]:
        return {
            "zips_as_dirs": zips_as_dirs,
        }

    async def get_wrappers_factory(self, wrapper_type: str) -> DirWrapperConstructor:
        cache = self.get_wrappers().get(wrapper_type)

        if cache is None:
            raise TgmountError(f"Missing wrapper with type: {wrapper_type}")

        return cache
