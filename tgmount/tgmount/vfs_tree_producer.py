from tgmount import vfs
from tgmount.util import none_fallback, yes
from tgmount.util.timer import Timer

from .logger import module_logger as logger
from .root_config_reader import TgmountConfigReader
from .root_config_types import RootConfigWalkingContext
from .tgmount_types import TgmountResources
from .types import TgmountRootType
from .vfs_tree import VfsTree, VfsTreeDir
from .vfs_tree_producer_types import VfsDirConfig


class VfsTreeProducer:
    """Class that using `TgmountResources` and `VfsStructureConfig` produces content into `VfsTreeDir` or `VfsTree`"""

    logger = logger.getChild(f"VfsTreeProducer")
    LOG_DEPTH = 2

    def __init__(self, resources: TgmountResources) -> None:
        self._resources = resources

    def __repr__(self) -> str:
        return f"VfsTreeProducer()"

    async def produce(
        self,
        tree_dir: VfsTreeDir | VfsTree,
        dir_config: TgmountRootType,
        ctx=None,
    ):
        """Produce content into `tree_dir` using `dir_config`"""
        config_reader = TgmountConfigReader()

        t1 = Timer()
        t1.start("producer")

        async for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            dir_config,
            resources=self._resources,
            ctx=none_fallback(
                ctx, RootConfigWalkingContext.from_resources(self._resources)
            ),
        ):
            await self.produce_from_config(tree_dir, path, vfs_config)

        t1.stop()

        # self.logger.trace(
        #     f"Done producing {tree_dir.path}. {t1.intervals[0].duration:.2f} ms"
        # )

    async def produce_from_config(
        self,
        tree_dir: VfsTreeDir | VfsTree,
        path: str,
        vfs_config: VfsDirConfig,
        # ctx: RootConfigContext,
    ):
        """Using `VfsDirConfig` produce content into `tree_dir`"""
        global_path = vfs.path_join(tree_dir.path, path)

        if len(vfs.napp(global_path, True)) <= self.LOG_DEPTH:
            self.logger.info(f"Producing {global_path}")
        else:
            self.logger.debug(f"Producing {global_path}")

        # create the subdir
        sub_dir = await tree_dir.create_dir(path)

        # If the directory has any wrapper
        if vfs_config.vfs_wrappers is not None:
            # self.logger.debug(
            #     f"{sub_dir.path} has {len(vfs_config.vfs_wrappers)} wrappers"
            # )

            for wrapper_cls, wrapper_arg in vfs_config.vfs_wrappers:
                wrapper = wrapper_cls.from_config(
                    none_fallback(wrapper_arg, {}), sub_dir
                )
                sub_dir.add_wrapper(wrapper)

        # If the directory has any producer
        if (
            vfs_config.vfs_producer is not None
            and vfs_config.vfs_producer_config is not None
        ):
            # self.logger.debug(f"{sub_dir.path} uses {vfs_config.vfs_producer} producer")

            producer = await vfs_config.vfs_producer.from_config(
                self._resources,
                vfs_config.vfs_producer_config,
                none_fallback(vfs_config.vfs_producer_arg, {}),
                sub_dir,
            )
            await producer.produce()

        # elif yes(vfs_config.vfs_producer) and isinstance(
        #     vfs_config.vfs_producer, VfsTreeProducerWithoutConfigProto
        # ):
        #     producer = await vfs_config.vfs_producer.from_config(
        #         resources=self._resources,
        #         vfs_tree_dir=sub_dir,
        #         arg={},
        #     )

        #     await producer.produce()
