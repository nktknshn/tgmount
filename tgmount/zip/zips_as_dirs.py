from typing import Iterable, Mapping, Sequence
from tgmount import vfs
from tgmount.vfs.types.dir import DirContentItem
from tgmount.zip.zip_dir_factory import DirContentZipFactory
from dataclasses import dataclass
from .zip_dir import DirContentZip


@dataclass
class ZipsAsDirsHandle:
    items: list[vfs.DirContentItem]


class ZipsAsDirs(vfs.DirContentProto[ZipsAsDirsHandle]):
    def __init__(
        self,
        source_dir_content: vfs.DirContentProto,
        *,
        dir_content_zip_factory: DirContentZipFactory = DirContentZipFactory(),
        hide_sources=True,
        skip_folder_if_single_subfolder=False,
        zip_file_like_to_dir_name=lambda item: f"{item.name}_unzipped",
        recursive=False,
    ):
        self._source_dir_content = source_dir_content
        self._dir_content_zip_factory = dir_content_zip_factory

        self._opt_hide_sources = hide_sources
        self._opt_skip_folder_if_single_subfolder = skip_folder_if_single_subfolder
        self._opt_zip_file_like_to_dir_name = zip_file_like_to_dir_name
        self._opt_recursive = recursive

    async def wrap_dir_content(self, dir_content: vfs.DirContentProto):
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
                await self.wrap_dir_content(dir_like.content),
            )

        result_items.append(dir_like)

    async def _process_file_like(
        self,
        result_items: list[DirContentItem],
        file_like: vfs.FileLike,
    ):
        zip_tree = await self._dir_content_zip_factory.get_zip_tree(file_like.content)

        zip_tree_root_items_names = list(zip_tree.keys())
        zip_tree_root_items = list(zip_tree.values())

        root_item = zip_tree_root_items[0]

        if self._opt_skip_folder_if_single_subfolder and isinstance(root_item, dict):
            zip_dir_name = zip_tree_root_items_names[0]
            zip_dir = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    file_like.content,
                    root_item,
                )
            )
        else:
            zip_dir_name = file_like.name
            zip_dir = (
                await self._dir_content_zip_factory.create_dir_content_from_ziptree(
                    file_like.content, zip_tree
                )
            )

        if self._opt_recursive:
            result_items.append(
                vfs.DirLike(
                    zip_dir_name,
                    await self.wrap_dir_content(zip_dir),
                ),
            )
        else:
            result_items.append(
                vfs.DirLike(zip_dir_name, zip_dir),
            )

    async def _create_dir_content(
        self,
        source_dir_content: vfs.DirContentProto,
    ):
        content_items = await vfs.read_dir_content(source_dir_content)

        result_items = []

        for item in content_items:
            if isinstance(item, vfs.DirLike):
                await self._process_dir_like(result_items, item)
            else:
                await self._process_file_like(result_items, item)

        return result_items

    async def opendir_func(self):
        return ZipsAsDirsHandle(
            await self._create_dir_content(self._source_dir_content),
        )

    async def readdir_func(
        self, handle: ZipsAsDirsHandle, off: int
    ) -> Iterable[vfs.DirContentItem]:
        return handle.items[off:]

    async def releasedir_func(self, handle):
        # underlying dir content has been already released in open function
        pass


def zips_as_dirs(
    tree_or_content: vfs.FsSourceTree | vfs.DirContentProto | Iterable[vfs.FileLike],
    **kwargs,
) -> "ZipsAsDirs":
    """
    may be recursive
    must support zip options
    """
    if vfs.is_tree(tree_or_content):
        return ZipsAsDirs(
            vfs.create_dir_content_from_tree(tree_or_content),
            **kwargs,
        )
    elif isinstance(tree_or_content, Iterable):
        return ZipsAsDirs(
            vfs.dir_content(*tree_or_content),  # type: ignore
            **kwargs,
        )

    return ZipsAsDirs(tree_or_content, **kwargs)


def zip_as_dir(
    file: vfs.FileLike,
):
    return vfs.DirLike(
        file.name,
        DirContentZip.create_dir_content_zip(file.content),
    )


def zip_as_dir_in_content(
    content: vfs.DirContentProto,
):
    return vfs.map_dir_content_items(
        lambda item: zip_as_dir(item)
        if vfs.FileLike.guard(item) and item.name.endswith(".zip")
        else item,
        content,
    )


async def zip_as_dir_async(
    file: vfs.FileLike,
):
    return vfs.DirLike(
        file.name,
        DirContentZip.create_dir_content_zip(file.content),
    )


def zip_as_dir_s(
    *,
    skip_folder_if_single_subfolder=False,
    skip_folder_prefix=None,
):
    async def _zip_as_dir_s(
        file: vfs.FileLike,
    ):

        if skip_folder_if_single_subfolder:
            root_dir_name = await DirContentZip(file.content).get_single_root_dir()

            if root_dir_name:
                return vfs.DirLike(
                    root_dir_name
                    if skip_folder_prefix is None
                    else f"{skip_folder_prefix}_{root_dir_name}",
                    DirContentZip.create_dir_content_zip(file.content, [root_dir_name]),
                )

        return vfs.DirLike(
            file.name,
            DirContentZip.create_dir_content_zip(file.content),
        )

    return _zip_as_dir_s
