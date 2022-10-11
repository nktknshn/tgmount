from dataclasses import dataclass
from typing import Iterable, Optional

from tgmount import tglog
from tgmount import vfs
from tgmount.vfs.types.dir import DirContentItem
from tgmount.zip.zip_dir_factory import DirContentZipFactory
from .util import get_uniq_name


@dataclass
class ZipsAsDirsHandle:
    items: list[vfs.DirContentItem]


class ZipsAsDirs(vfs.DirContentProto[ZipsAsDirsHandle]):
    """Wraps `vfs.DirContentProto` to turn contained zip files into folders"""

    async def opendir_func(self):
        return ZipsAsDirsHandle(
            await self._get_dir_content_items(self._wrapped_dir_content),
        )

    async def readdir_func(
        self, handle: ZipsAsDirsHandle, off: int
    ) -> Iterable[vfs.DirContentItem]:
        return handle.items[off:]

    async def releasedir_func(self, handle):
        # underlying dir content has been already released in open function
        pass

    def __init__(
        self,
        wrapped_dir_content: vfs.DirContentProto,
        *,
        dir_content_zip_factory: Optional[DirContentZipFactory] = None,
        hide_sources=True,
        skip_folder_if_single_subfolder=False,
        skip_folder_if_single_subfolder_exclude={"__MACOSX"},
        zip_file_like_to_dir_name=lambda item: f"{item.name}_unzipped",
        recursive=False,
    ):
        self._logger = tglog.getLogger(f"ZipsAsDirs()")

        self._wrapped_dir_content = wrapped_dir_content

        self._dir_content_zip_factory = (
            dir_content_zip_factory
            if dir_content_zip_factory is not None
            else DirContentZipFactory()
        )

        self._opt_hide_sources = hide_sources
        self._opt_skip_folder_if_single_subfolder = skip_folder_if_single_subfolder
        self._opt_skip_folder_if_single_subfolder_exclude = (
            skip_folder_if_single_subfolder_exclude
        )
        self._opt_zip_file_like_to_dir_name = zip_file_like_to_dir_name
        self._opt_recursive = recursive

    async def _wrap_dir_content(self, dir_content: vfs.DirContentProto):
        return ZipsAsDirs(
            dir_content,
            dir_content_zip_factory=self._dir_content_zip_factory,
            hide_sources=self._opt_hide_sources,
            recursive=self._opt_recursive,
            skip_folder_if_single_subfolder=self._opt_skip_folder_if_single_subfolder,
            zip_file_like_to_dir_name=self._opt_zip_file_like_to_dir_name,
        )

    async def _process_dir_like(
        self,
        result_items: list[DirContentItem],
        dir_like: vfs.DirLike,
    ):

        if self._opt_recursive:
            dir_like = vfs.DirLike(
                dir_like.name,
                await self._wrap_dir_content(dir_like.content),
            )

        result_items.append(dir_like)

    async def _process_zip(
        self,
        result_items: list[DirContentItem],
        zip_file_like: vfs.FileLike,
    ):

        zip_tree = await self._dir_content_zip_factory.get_ziptree(
            zip_file_like.content
        )

        zip_tree_root_items_names = list(
            set(zip_tree.keys()).difference(
                self._opt_skip_folder_if_single_subfolder_exclude
            )
        )

        zip_tree_root_items = list(zip_tree[k] for k in zip_tree_root_items_names)

        root_item = zip_tree_root_items[0]

        if self._opt_skip_folder_if_single_subfolder and isinstance(root_item, dict):
            # if there is only one item in the root of the zip file
            if isinstance(zip_file_like.extra, tuple):
                message_id = zip_file_like.extra[0]
                zip_dir_name = f"{message_id}_{zip_tree_root_items_names[0]}"
            else:
                zip_dir_name = zip_tree_root_items_names[0]

            zip_dir = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file_like.content,
                    root_item,
                )
            )
        else:
            zip_dir_name = zip_file_like.name
            zip_dir = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    zip_file_like.content, zip_tree
                )
            )

        zip_dir_name = get_uniq_name(
            list(map(lambda a: a.name, result_items)), zip_dir_name
        )

        result_items.append(
            vfs.DirLike(
                zip_dir_name,
                zip_dir,
                extra=zip_file_like.extra,
            ),
        )

    async def _get_dir_content_items(
        self,
        source_dir_content: vfs.DirContentProto,
    ) -> list[vfs.DirContentItem]:

        content_items = await vfs.dir_content_read(source_dir_content)

        result_items = []

        # XXX reversed???
        for item in reversed(list(content_items)):
            if isinstance(item, vfs.DirLike):
                await self._process_dir_like(result_items, item)
            else:
                if item.name.endswith(".zip"):
                    try:
                        await self._process_zip(result_items, item)
                    except:
                        result_items.append(item)
                else:
                    result_items.append(item)

        return result_items


def zips_as_dirs(
    tree_or_content: vfs.DirContentSource,
    **kwargs,
) -> "ZipsAsDirs":
    """
    may be recursive
    must support zip options
    """
    if vfs.is_tree(tree_or_content):
        return ZipsAsDirs(
            vfs.dir_content_from_source(tree_or_content),
            **kwargs,
        )
    elif isinstance(tree_or_content, Iterable):
        return ZipsAsDirs(
            vfs.dir_content(*tree_or_content),  # type: ignore
            **kwargs,
        )

    return ZipsAsDirs(tree_or_content, **kwargs)
