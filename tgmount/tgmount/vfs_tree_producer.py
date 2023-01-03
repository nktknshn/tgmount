from tgmount import vfs, tglog
from tgmount.util import none_fallback
from .vfs_tree_producer_types import VfsStructureConfig

from .root_config_reader import TgmountConfigReader
from .root_config_types import RootConfigContext
from .tgmount_types import TgmountResources
from .types import TgmountRootSource
from .vfs_tree import VfsTreeDir, VfsTree
from .vfs_tree_wrapper import WrapperEmpty, WrapperZipsAsDirs


class VfsTreeProducer:
    """Class that using `TgmountResources` and `VfsStructureConfig` produces content into `VfsTreeDir` or `VfsTree`"""

    def __init__(self, resources: TgmountResources) -> None:

        self._logger = tglog.getLogger(f"VfsTreeProducer()")
        self._resources = resources

    def __repr__(self) -> str:
        return f"VfsTreeProducer()"

    async def produce_at(
        self,
        tree_dir: VfsTreeDir | VfsTree,
        path: str,
        vfs_config: VfsStructureConfig,
        ctx: RootConfigContext,
    ):
        self._logger.debug(f"produce: {vfs.path_join(tree_dir.path, path)}")

        if vfs_config.source_dict.get("wrappers") == "ExcludeEmptyDirs":
            # print(vfs_config.source_dict.get("wrappers"))
            sub_dir = await tree_dir.create_dir(path)
            sub_dir._wrappers.append(WrapperEmpty(sub_dir))
        elif vfs_config.source_dict.get("wrappers") == "ZipsAsDirs":
            # print(vfs_config.source_dict.get("wrappers"))
            sub_dir = await tree_dir.create_dir(path)
            sub_dir._wrappers.append(WrapperZipsAsDirs(sub_dir))
        else:
            sub_dir = await tree_dir.create_dir(path)

        # if vfs_config.producer_config is not None:
        #     sub_dir.additional_data = vfs_config.producer_config.message_source

        if vfs_config.vfs_producer is not None:
            producer = await vfs_config.vfs_producer.from_config(
                self._resources,
                vfs_config,
                none_fallback(vfs_config.vfs_producer_arg, {}),
                sub_dir,
            )

            sub_dir._subs.append(producer)

            await producer.produce()

    async def produce(
        self,
        tree_dir: VfsTreeDir | VfsTree,
        dir_config: TgmountRootSource,
        ctx=None,
    ):
        """Produce content into `tree_dir` using `dir_config`"""
        config_reader = TgmountConfigReader()

        for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            dir_config,
            resources=self._resources,
            ctx=none_fallback(ctx, RootConfigContext.from_resources(self._resources)),
        ):
            await self.produce_at(tree_dir, path, vfs_config, ctx)

        self._logger.info(f"Done producing {tree_dir.path}")
