from typing import Mapping
from zipfile import BadZipFile
from tgmount import vfs, tglog, zip as z
from ..vfs_tree import VfsTreeDir
from ..vfs_tree_types import (
    TreeEventNewItems,
    TreeEventRemovedDirs,
    TreeEventNewDirs,
    TreeEventRemovedItems,
    TreeEventType,
)

from ..vfs_tree_wrapper import VfsTreeWrapperProto

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class WrapperZipsAsDirs(VfsTreeWrapperProto):
    logger = tglog.getLogger(f"WrapperZipsAsDirs")

    @classmethod
    def from_config(cls, arg: Mapping, sub_dir: VfsTreeDir):
        WrapperZipsAsDirs(sub_dir)

    def __init__(self, wrapped_dir: "VfsTreeDir") -> None:
        self._wrapped_dir = wrapped_dir

        self._zip_factory = z.DirContentZipFactory()
        self._zip_to_folder: dict[str, vfs.DirLike] = {}

    async def _add_zip_file(self, zip_file_like: vfs.FileLike) -> vfs.DirLike:

        zt = await self._zip_factory.get_ziptree(zip_file_like.content)
        dc = await self._zip_factory.create_dir_content_from_ziptree(
            zip_file_like.content, zt
        )

        dirlike = self._zip_to_folder[zip_file_like.name] = vfs.DirLike(
            zip_file_like.name, dc
        )

        return dirlike

    async def _remove_zip_file(self, zip_file_like: vfs.FileLike):
        del self._zip_to_folder[zip_file_like.name]

    async def _is_zip_file(self, zip_file_like: vfs.FileLike):
        return zip_file_like.name.endswith(".zip")

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:

        items = []

        for item in await vfs.dir_content_read(dir_content):
            if item.name in self._zip_to_folder:
                items.append(self._zip_to_folder[item.name])
            else:
                items.append(item)

        return vfs.DirContentList(items)

    async def wrap_events(
        self, source: "VfsTreeDir", events: list[TreeEventType]
    ) -> list[TreeEventType]:
        """Catch updates related to zip files and process them in a propriate
        way.

        If a zip file appears: add a corresponding folder.
        If a zip file has gone remove the folder.

        """
        # parent = await child.get_parent()

        # we only handle the wrapped dir ignoring nested dirs
        if source != self._wrapped_dir:
            return events

        modified_updates = []

        for e in events:
            if isinstance(e, TreeEventNewItems):
                _e = TreeEventNewItems(e.update_path, [])

                for item in e.new_items:
                    if isinstance(item, vfs.FileLike) and await self._is_zip_file(item):
                        try:
                            dirlike = await self._add_zip_file(item)
                            _e.new_items.append(dirlike)
                        except BadZipFile:
                            # bad zip
                            self.logger.error(f"{item} is a bad zip file")
                            _e.new_items.append(item)
                    else:
                        _e.new_items.append(item)
                modified_updates.append(_e)

            elif isinstance(e, TreeEventRemovedItems):
                _e = TreeEventRemovedItems(e.update_path, [])

                for item in e.removed_items:
                    if isinstance(item, vfs.FileLike) and item in self._zip_to_folder:
                        _item = self._zip_to_folder[item]
                        _e.removed_items.append(_item)
                        await self._remove_zip_file(item)
                    else:
                        _e.removed_items.append(item)

                modified_updates.append(_e)
            else:
                modified_updates.append(e)

        return modified_updates
