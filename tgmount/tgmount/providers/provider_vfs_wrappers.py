from typing import Mapping, Type

from tgmount.tgmount.vfs_tree_wrapper import VfsTreeWrapperProto


class ProviderVfsWrappersBase:
    wrappers: Mapping[str, Type[VfsTreeWrapperProto]]

    # def __init__(self):
    #     self._producers = {}

    def get_by_name(self, name: str) -> Type[VfsTreeWrapperProto] | None:
        return self.wrappers.get(name)
