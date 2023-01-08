from tgmount import vfs, tglog
from ..vfs_tree import VfsTreeDir
from ..vfs_tree_types import (
    TreeEventRemovedDirs,
    TreeEventNewDirs,
    TreeEventType,
)
from ..vfs_tree_wrapper import VfsTreeWrapperProto

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)

from tgmount import vfs


async def filter_empty(item: vfs.DirContentItem):

    if vfs.DirLike.guard(item):
        return len(list(await vfs.dir_content_read(item.content))) > 0

    return True


def remove_empty_dirs_content(
    d: vfs.DirContentProto,
) -> vfs.DirContentProto:
    return vfs.dir_content_filter_items(filter_empty, d)


class WrapperEmpty(VfsTreeWrapperProto):
    @classmethod
    def from_config(cls, arg, sub_dir):
        return WrapperEmpty(sub_dir)

    def __init__(self, wrapped_dir: "VfsTreeDir") -> None:
        self._wrapped_dir = wrapped_dir
        self._wrapped_dir_subdirs: set["VfsTreeDir"] = set()
        self._logger = tglog.getLogger(f"WrapperEmpty({self._wrapped_dir})")

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        return remove_empty_dirs_content(dir_content)

    async def _get_subdirs_names(self, child: "VfsTreeDir") -> set[str]:
        return set(sd.name for sd in await child.get_subdirs())

    async def _is_empty(self, subdir: "VfsTreeDir") -> bool:
        sds = await subdir.get_subdirs()
        cs = await subdir.get_dir_content_items()

        return (len(sds) + len(cs)) == 0

    async def wrap_events(
        self,
        child: "VfsTreeDir",
        events: list[TreeEventType],
    ) -> list[TreeEventType]:

        parent = await child.get_parent()

        # we ignore nested folders
        if parent != self._wrapped_dir:
            return events

        self._logger.debug(f"from {child} events: {events}")

        # if not await self._wrapped_dir.tree.exists(child):
        #     return events

        is_empty = await self._is_empty(child)
        # print(
        #     f"self={self._wrapped_dir.path} child={child.path} is_empty={is_empty} wrapped_subdirs={self._wrapped_dir_subdirs} updates={updates}"
        # )

        if child in self._wrapped_dir_subdirs:
            if is_empty:
                events = [TreeEventRemovedDirs([child.path])]
        else:
            if not is_empty:
                events = [
                    TreeEventNewDirs([child.path]),
                    *events,
                ]
                self._wrapped_dir_subdirs.add(child)

        return events
