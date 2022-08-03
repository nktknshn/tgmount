import logging


from tgmount import fs, vfs
from tgmount import zip as z

from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tgclient import TelegramSearch, TgmountTelegramClient, guards
from tgmount.vfs import FsSourceTree, text_content
from tgmount.vfs.file import vfile

logger = logging.getLogger("tgvfs")


async def tgclient(
    tgapp_api: tuple[int, str],
    session_name="tgfs",
):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def create_test(
    telegram_id: str,
    messages_source: TelegramSearch,
    tgfiles: TelegramFilesSource,
    limit=None,
) -> FsSourceTree:

    cache = CacheFactoryMemory(blocksize=256 * 1024)
    caching = FilesSourceCaching(tgfiles, cache)

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    texts = [
        vfile(
            fname=f"{msg.id}.txt",
            content=text_content(msg.message + "\n"),
            creation_time=msg.date,
        )
        for msg in messages
        if guards.MessageWithText.guard(msg)
    ]

    photos = [
        tgfiles.file(msg) for msg in messages if guards.MessageWithPhoto.guard(msg)
    ]

    videos = [
        tgfiles.file(msg) for msg in messages if guards.MessageWithVideo.guard(msg)
    ]

    music = [
        tgfiles.file(msg) for msg in messages if guards.MessageWithMusic.guard(msg)
    ]

    # it's recommended to use cache with zip archives since
    # OS cache will not be applied to the archive file itself

    zips = [caching.file(msg) for msg in messages if guards.MessageWithZip.guard(msg)]

    # sadly files seeking inside a zip works by reading the offset bytes so it's slow
    # https://github.com/python/cpython/blob/main/Lib/zipfile.py#L1116

    # also id3v1 tags are stored in the end of a file :)
    # https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_id3v1.py#L34

    # and most of the players try to read it. So just adding an mp3 or flac
    # to a player will fetch the whole file from the archive

    # setting hacky_handle_mp3_id3v1 will patch reading function so it
    # always returns 4096 zero bytes when reading a block of 4096 bytes
    # (usually players read this amount looking for id3v1 (requires
    # investigation to find a less hacky way)) from an mp3 or flac file
    # inside a zip archive

    return {
        "texts": texts,
        "photos": photos,
        "videos": videos,
        "music": music,
        "zips": z.zips_as_dirs(
            zips,
            hacky_handle_mp3_id3v1=True,
            skip_folder_if_single_subfolder=True,
        ),
        "all_that": z.zips_as_dirs(
            [
                *texts,
                *photos,
                *videos,
                *music,
                *zips,
            ],
            hacky_handle_mp3_id3v1=True,
            skip_folder_if_single_subfolder=True,
        ),
    }


async def mount():
    init_logging(debug=True)

    client = await tgclient(read_tgapp_api())

    messages_source = client
    documents_source = TelegramFilesSource(client)

    vfs_root = vfs.root(
        {
            "test": await create_test(
                "tgmounttestingchannel",
                messages_source,
                documents_source,
            ),
        }
    )

    ops = fs.FileSystemOperations(vfs_root)

    await mount_ops(ops, "/home/hrn/mnt/tgmount1")


if __name__ == "__main__":
    run_main(mount)
