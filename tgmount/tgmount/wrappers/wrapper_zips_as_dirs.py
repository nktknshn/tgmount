from dataclasses import dataclass, field
from typing import Callable, Mapping
from zipfile import BadZipFile

from tgmount import vfs
from tgmount import zip as z

from ..vfs_tree import VfsTreeDir
from ..vfs_tree_types import (
    TreeEventNewDirs,
    TreeEventNewItems,
    TreeEventRemovedDirs,
    TreeEventRemovedItems,
    TreeEventType,
)
from ..vfs_tree_wrapper_types import VfsTreeWrapperProto
from .logger import logger as _logger


@dataclass
class WrapperZipsAsDirsProps:
    fix_id3v1: bool
    """ Many media players try to read id3v1 tag which is located in the end of a media file. Since `zipfile` module doesn't support seeking this leads to fetching whole file just to start playing"""

    hide_zip_files: bool
    skip_single_root_subfolder: bool
    skip_single_root_subfolder_exclude_from_root: frozenset[str]
    dir_name_mapper: Callable[[vfs.FileLike], str]

    @staticmethod
    def from_config(config: Mapping):
        hide_zip_files = config.get("hide_zip_files", True)

        return WrapperZipsAsDirsProps(
            hide_zip_files=hide_zip_files,
            fix_id3v1=config.get("fix_id3v1", True),
            skip_single_root_subfolder=config.get("skip_single_root_subfolder", True),
            skip_single_root_subfolder_exclude_from_root=frozenset({"__MACOSX"}),
            dir_name_mapper=lambda item: item.name
            if hide_zip_files
            else f"{item.name}_unzipped",
        )


class WrapperZipsAsDirs(VfsTreeWrapperProto):
    """
    Wraps `VfsTreeDir`.

    Turns contained zip files into directories.

    """

    logger = _logger.getChild(f"WrapperZipsAsDirs")

    @classmethod
    def from_config(cls, arg: Mapping, sub_dir: VfsTreeDir):
        return WrapperZipsAsDirs(
            sub_dir,
            WrapperZipsAsDirsProps.from_config(arg),
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

    async def wrap_events(self, events: list[TreeEventType]) -> list[TreeEventType]:
        """

        Catch changes in the wrapped directory

        If a zip file appears - add a corresponding folder.
        If a zip file has gone - remove the folder.

        """

        # we only handle the wrapped dir ignoring nested dirs

        _events = []

        for e in events:
            if e.sender != self._wrapped_dir:
                return events

            # when items appear
            if isinstance(e, TreeEventNewItems):
                _e = TreeEventNewItems(sender=e.sender, new_items=[])

                for item in e.new_items:
                    await self._process_event_new_item(e, _e, item)

                _events.append(_e)

            # when items disappear
            elif isinstance(e, TreeEventRemovedItems):
                _e = TreeEventRemovedItems(sender=e.sender, removed_items=[])

                for item in e.removed_items:
                    if (
                        isinstance(item, vfs.FileLike)
                        and item.name in self._zip_to_dirlike
                    ):
                        _item = self._zip_to_dirlike[item.name]
                        _e.removed_items.append(_item)

                        if not self._props.hide_zip_files:
                            _e.removed_items.append(item)

                        await self._remove_zip_file(item)
                    else:
                        _e.removed_items.append(item)

                _events.append(_e)
            else:
                _events.append(e)

        return _events

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
            if isinstance(zip_file_like.extra, tuple):
                # if there is a source message info in the extra
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
            zip_dir_name = self._props.dir_name_mapper(zip_file_like)
            zip_dir_content = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file_like.content, zip_tree
                )
            )

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
                if not self._props.hide_zip_files:
                    items.append(item)
            else:
                items.append(item)

        return vfs.DirContentList(items)
