from dataclasses import dataclass, field
from typing import Callable, Mapping
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

from ..vfs_tree_wrapper_types import VfsTreeWrapperProto

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


@dataclass
class WrapperZipsAsDirsProps:
    fix_id3v1: bool = True
    """ Many media players tries to read id3v1 tag which is located in the end of the file. Since zipfile module doesn't support seeking this leads to  """

    hide_zip_files: bool = True
    skip_single_root_subfolder: bool = True
    skip_single_root_subfolder_exclude_from_root: frozenset[str] = frozenset(
        {"__MACOSX"}
    )
    dir_name_mapper: Callable[[vfs.FileLike], str] = lambda item: item.name

    @staticmethod
    def from_config(config: Mapping):
        return WrapperZipsAsDirsProps()


class WrapperZipsAsDirs(VfsTreeWrapperProto):
    """
    Wraps `VfsTreeDir`.

    Turns contained zip files into directories.



    """

    logger = tglog.getLogger(f"WrapperZipsAsDirs")

    @classmethod
    def from_config(cls, arg: Mapping, sub_dir: VfsTreeDir):
        return WrapperZipsAsDirs(
            sub_dir,
            WrapperZipsAsDirsProps(
                fix_id3v1=arg.get(
                    "fix_id3v1",
                    True,
                )
            ),
        )

    def __init__(
        self,
        wrapped_dir: "VfsTreeDir",
        props: WrapperZipsAsDirsProps,
    ) -> None:
        self._wrapped_dir = wrapped_dir

        self._dir_content_zip_factory = z.DirContentZipFactory.create_from_props(
            fix_Id3v1=props.fix_id3v1
        )

        self._zip_to_dirlike: dict[str, vfs.DirLike] = {}
        self._other_items: dict[str, vfs.DirContentItem] = {}

        self._props = props

    async def wrap_events(
        self, events_sender: "VfsTreeDir", events: list[TreeEventType]
    ) -> list[TreeEventType]:
        """

        Catch changes in the wrapped directory

        If a zip file appears - add a corresponding folder.
        If a zip file has gone - remove the folder.

        """

        # we only handle the wrapped dir ignoring nested dirs
        if events_sender != self._wrapped_dir:
            return events

        modified_events = []

        for e in events:
            # when items appear
            if isinstance(e, TreeEventNewItems):
                _e = TreeEventNewItems(e.update_path, [])

                for item in e.new_items:
                    await self._process_event_new_item(e, _e, item)

                modified_events.append(_e)

            # when items disappear
            elif isinstance(e, TreeEventRemovedItems):
                _e = TreeEventRemovedItems(e.update_path, [])

                for item in e.removed_items:
                    if isinstance(item, vfs.FileLike) and item in self._zip_to_dirlike:
                        _item = self._zip_to_dirlike[item]
                        _e.removed_items.append(_item)
                        await self._remove_zip_file(item)
                    else:
                        _e.removed_items.append(item)

                modified_events.append(_e)
            else:
                modified_events.append(e)

        return modified_events

    async def _process_event_new_item(
        self,
        orig_event: TreeEventNewItems,
        result_event: TreeEventNewItems,
        item: vfs.DirContentItem,
    ):
        if isinstance(item, vfs.FileLike) and await self._is_zip_file(item):
            try:
                dirlike = await self._add_zip_file(item)

                result_event.new_items.append(dirlike)

                if not self._props.hide_zip_files:
                    result_event.new_items.append(item)

            except BadZipFile:
                # bad zip
                self.logger.error(f"{item} is a bad zip file")
                result_event.new_items.append(item)
        else:
            result_event.new_items.append(item)

    async def _add_zip_file(self, zip_file_like: vfs.FileLike) -> vfs.DirLike:

        zip_tree = await self._dir_content_zip_factory.get_ziptree(
            zip_file_like.content
        )

        zip_tree_root_items_names = list(
            set(zip_tree.keys()).difference(
                self._props.skip_single_root_subfolder_exclude_from_root
            )
        )

        zip_tree_root_items = list(zip_tree[k] for k in zip_tree_root_items_names)

        # if root_item is dict, it is a directory
        root_item = zip_tree_root_items[0]

        if (
            self._props.skip_single_root_subfolder
            and isinstance(root_item, dict)
            and len(zip_tree_root_items) == 1
        ):
            # handle skip_single_root_subfolder props
            # if there is a source message info in the extra
            if isinstance(zip_file_like.extra, tuple):
                message_id = zip_file_like.extra[0]
                zip_dir_name = f"{message_id}_{zip_tree_root_items_names[0]}"
            else:
                zip_dir_name = zip_tree_root_items_names[0]

            zip_dir_content = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file_like.content,
                    root_item,
                )
            )
        else:
            zip_dir_name = zip_file_like.name
            zip_dir_content = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file_like.content, zip_tree
                )
            )

        # dc = await self._dir_content_zip_factory.create_dir_content_from_ziptree(
        #     zip_file_like.content, zip_tree
        # )

        dirlike = self._zip_to_dirlike[zip_file_like.name] = vfs.DirLike(
            zip_dir_name, zip_dir_content, extra=zip_file_like.extra
        )

        return dirlike

    async def _remove_zip_file(self, zip_file_like: vfs.FileLike):
        del self._zip_to_dirlike[zip_file_like.name]

    async def _is_zip_file(self, zip_file_like: vfs.FileLike):
        return zip_file_like.name.endswith(".zip")

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:

        items = []

        for item in await vfs.dir_content_read(dir_content):
            if item.name in self._zip_to_dirlike:
                items.append(self._zip_to_dirlike[item.name])
            else:
                items.append(item)

        return vfs.DirContentList(items)
