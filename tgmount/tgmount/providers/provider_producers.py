from typing import Mapping, Type

from tgmount.tgmount.vfs_tree_producer_types import VfsTreeProducerProto


class ProducersProviderBase:
    producers: Mapping[str, Type[VfsTreeProducerProto]]

    # def __init__(self):
    #     self._producers = {}

    def get_by_name(self, name: str) -> Type[VfsTreeProducerProto] | None:
        return self.producers.get(name)
