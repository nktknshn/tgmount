from tgmount import vfs, tglog, zip as z
from ..vfs_tree import VfsTreeDir
from ..vfs_tree_types import UpdateRemovedDirs, UpdateNewDirs, UpdateType, Wrapper

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class WrapperZipsAsDirs(Wrapper):
    def __init__(self, wrapped_dir: "VfsTreeDir") -> None:
        self._wrapped_dir = wrapped_dir

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        return z.ZipsAsDirs(dir_content)

    async def wrap_updates(
        self, child: "VfsTreeDir", updates: list[UpdateType]
    ) -> list[UpdateType]:
        """Catch updates related to zip files and process them in a propriate
        way.

        If a zip file appears: add a corresponding folder.
        If a zip file has gone remove the folder.

        """
        # print(updates)
        parent = await child.get_parent()

        # we ignore nested folders
        if parent != self._wrapped_dir:
            return updates

        return []
