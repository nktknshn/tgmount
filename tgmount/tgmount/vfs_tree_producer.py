from tgmount import vfs, tglog
from tgmount.util import none_fallback
from .vfs_tree_producer_types import VfsStructureConfig

from .root_config_reader import TgmountConfigReader
from .root_config_types import RootConfigContext
from .tgmount_types import TgmountResources
from .types import (
    TgmountRootSource,
)
from .vfs_tree import VfsTreeDir, VfsTree
from .vfs_tree_wrapper import WrapperEmpty, WrapperZipsAsDirs


class VfsTreeProducer:
    def __init__(self, resources: TgmountResources) -> None:

        self._logger = tglog.getLogger(f"VfsTreeProducer()")

        # self._dir_config = dir_config
        self._resources = resources

    def __repr__(self) -> str:
        return f"VfsTreeProducer()"

    async def produce(
        self, tree_dir: VfsTreeDir | VfsTree, dir_config: TgmountRootSource, ctx=None
    ):
        config_reader = TgmountConfigReader()

        for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            dir_config,
            resources=self._resources,
            ctx=none_fallback(ctx, RootConfigContext.from_resources(self._resources)),
        ):
            # print(f"produce: {vfs.path_join(tree_dir.path, path)}")
            self._logger.info(f"produce: {vfs.path_join(tree_dir.path, path)}")

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

            vfs_config: VfsStructureConfig

            if vfs_config.vfs_producer is not None:
                producer = await vfs_config.vfs_producer.from_config(
                    self._resources,
                    vfs_config,
                    none_fallback(vfs_config.vfs_producer_arg, {}),
                    sub_dir,
                )

                sub_dir._subs.append(producer)

                await producer.produce()

            # if (
            #     vfs_config.producer_config
            #     and vfs_config.vfs_producer_name
            #     and vfs_config.vfs_producer_name == "MessageBySender"
            # ):
            #     producer_arg = none_fallback(vfs_config.vfs_producer_arg, {})
            #     producer = VfsTreeDirByUser(
            #         config=vfs_config.producer_config,
            #         dir_cfg=producer_arg.get(
            #             "sender_root",
            #             VfsTreeDirByUser.DEFAULT_SENDER_ROOT_CONFIG,
            #         ),
            #         minimum=producer_arg.get("minimum", 1),
            #         resources=self._resources,
            #         tree_dir=sub_dir,
            #     )

            #     sub_dir._subs.append(producer)

            #     await producer.produce()
            # elif vfs_config.producer_config:
            #     producer = VfsTreePlainDir(sub_dir, vfs_config.producer_config)

            #     sub_dir._subs.append(producer)

            #     await producer.produce()
