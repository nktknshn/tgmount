from tgmount import vfs

from ..vfs_tree import VfsTreeDir
from ..vfs_tree_types import (
    TreeEventNewDirs,
    TreeEventRemovedDirs,
    TreeEventType,
    TreeEventRemovedItems,
    TreeEventNewItems,
)
from ..vfs_tree_wrapper_types import VfsTreeWrapperProto
from .logger import logger as _logger


async def filter_empty(item: vfs.DirContentItem):
    if vfs.DirLike.guard(item):
        return len(list(await vfs.dir_content_read(item.content))) > 0

    return True


def remove_empty_dirs_content(
    d: vfs.DirContentProto,
) -> vfs.DirContentProto:
    return vfs.dir_content_filter_items(filter_empty, d)


class WrapperEmpty(VfsTreeWrapperProto):
    """Exclude empty directories from this directory"""

    logger = _logger.getChild("WrapperEmpty")

    @classmethod
    def from_config(cls, arg, sub_dir):
        return WrapperEmpty(sub_dir)

    def __init__(self, wrapped_dir: "VfsTreeDir") -> None:
        self._wrapped_dir = wrapped_dir
        self._wrapped_nonempty_dir_subdirs: set["VfsTreeDir"] = set()
        self._logger = self.logger.getChild(self._wrapped_dir.path)

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        return remove_empty_dirs_content(dir_content)

    async def _get_subdirs_names(self, child: "VfsTreeDir") -> set[str]:
        return set(sd.name for sd in await child.get_subdirs())

    async def _is_empty(self, subdir: "VfsTreeDir") -> bool:
        # sds = await subdir.get_subdirs()
        cs = await subdir.get_dir_content()
        return await vfs.dir_is_empty(cs)
        # return (len(sds) + len(cs)) == 0

    async def wrap_events(
        self,
        events: list[TreeEventType[VfsTreeDir]],
    ) -> list[TreeEventType]:
        """We catch updates for the directory children"""
        self._logger.debug(f"wrap_events({events})")

        _events = []

        for ev in events:
            sender = ev.sender
            sender_parent = await sender.get_parent()

            if sender_parent == self._wrapped_dir:
                # for subfolder of the wrapped folder
                is_empty = await self._is_empty(sender)

                if sender in self._wrapped_nonempty_dir_subdirs:
                    # if the folder used to be not empty and visible
                    if is_empty:
                        # remove it
                        _events.append(
                            TreeEventRemovedDirs(
                                sender=self._wrapped_dir,
                                update_path=self._wrapped_dir.path,
                                removed_dirs=[sender.path],
                            )
                        )
                        self._wrapped_nonempty_dir_subdirs.discard(sender)
                    else:
                        # otherwrise just pass the events further
                        _events.append(ev)
                else:
                    if not is_empty:
                        # if the folder has not been visible yet and now it is
                        #  not empty, then show it to the file system
                        _events.extend(
                            [
                                TreeEventNewDirs(
                                    sender=self._wrapped_dir,
                                    update_path=self._wrapped_dir.path,
                                    new_dirs=[sender.path],
                                ),
                                ev,
                            ]
                        )
                        self._wrapped_nonempty_dir_subdirs.add(sender)

            elif sender == self._wrapped_dir:
                # catch new subfolder event
                if isinstance(ev, TreeEventNewDirs):
                    _e = TreeEventNewDirs(
                        sender=sender,
                        update_path=ev.update_path,
                        new_dirs=[],
                    )

                    # show only not empty subfolders
                    for dpath in ev.new_dirs:
                        d = await self._wrapped_dir.tree.get_dir(dpath)

                        if not await self._is_empty(d):
                            _e.new_dirs.append(dpath)
                            self._wrapped_nonempty_dir_subdirs.add(d)
                else:
                    _events.append(ev)
            else:
                _events.append(ev)

        return _events
