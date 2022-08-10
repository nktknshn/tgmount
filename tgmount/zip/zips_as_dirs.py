from typing import Iterable, Mapping, Sequence
from tgmount import vfs

from .zip_dir import DirContentZip, create_dir_content


class ZipsAsDirs:
    def __init__(
        self,
        source_dir_content: vfs.DirContentProto,
        *,
        hide_sources=True,
        skip_folder_if_single_subfolder=False,
        zip_file_like_to_dir_name=lambda item: f"{item.name}_unzipped",
    ):
        self._source_dir_content = source_dir_content
        self._hide_sources = hide_sources
        self._skip_folder_if_single_subfolder = skip_folder_if_single_subfolder
        self._zip_file_like_to_dir_name = zip_file_like_to_dir_name

    def zip_as_dir(
        self,
        file: vfs.FileLike,
    ):
        return vfs.DirLike(
            file.name,
            create_dir_content(file.content),
        )


def zip_as_dir(
    file: vfs.FileLike,
):
    return vfs.DirLike(
        file.name,
        create_dir_content(file.content),
    )


def zip_as_dir_in_content(
    content: vfs.DirContentProto,
):
    return vfs.map_dir_content(
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
        create_dir_content(file.content),
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
                    create_dir_content(file.content, [root_dir_name]),
                )

        return vfs.DirLike(
            file.name,
            create_dir_content(file.content),
        )

    return _zip_as_dir_s


def zips_as_dirs(
    tree_or_content: vfs.FsSourceTree | vfs.DirContentProto | Iterable[vfs.FileLike],
    **kwargs,
) -> ZipsAsDirs:
    """
    sadly files seeking inside a zip works by reading the offset bytes so it's slow
    https://github.com/python/cpython/blob/main/Lib/zipfile.py#L1116

    also id3v1 tags are stored in the end of a file :)
    https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_id3v1.py#L34

    and most of the players try to read it. So just adding an mp3 or flac
    to a player will fetch the whole file from the archive

    setting hacky_handle_mp3_id3v1 will patch reading function so it
    always returns 4096 zero bytes when reading a block of 4096 bytes
    (usually players read this amount looking for id3v1 (requires
    investigation to find a less hacky way)) from an mp3 or flac file
    inside a zip archive
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
