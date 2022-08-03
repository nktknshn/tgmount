import logging


from tgmount import fs, vfs
from tgmount import zip as z

from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tgclient import TelegramSearch, TgmountTelegramClient, guards
from tgmount.vfs import FsSourceTree, text_content

logger = logging.getLogger("tgvfs")


async def tgclient(tgapp_api: tuple[int, str], session_name="tgfs"):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


async def create_test(
    telegram_id: str,
    messages_source: TelegramSearch,
    tgfiles: TelegramFilesSource,
    limit=3000,
) -> FsSourceTree:

    cache = CacheFactoryMemory(blocksize=128 * 1024)
    caching = FilesSourceCaching(tgfiles, cache)

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    texts = [
        (f"{msg.id}.txt", text_content(msg.message))
        for msg in messages
        if guards.MessageWithText.guard(msg)
    ]

    photos = [
        (f"{msg.id}_photo.jpeg", tgfiles.content(msg))
        for msg in messages
        if guards.MessageWithPhoto.guard(msg)
    ]

    videos = [
        (f"{msg.id}_document{msg.file.ext}", tgfiles.content(msg))
        for msg in messages
        if guards.MessageWithVideo.guard(msg)
    ]

    music = [
        (f"{msg.id}_{msg.file.name}", tgfiles.content(msg))
        for msg in messages
        if guards.MessageWithMusic.guard(msg)
    ]

    # it's recommended to use cache with zip archives since
    # OS cache will not be applied to the archive file itself

    # sadly files seeking works by reading the offset bytes in zip archives
    # https://github.com/python/cpython/blob/main/Lib/zipfile.py#L1116

    # and sadly id3v1 tags are stored in the end of an mp3 file :)
    # https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_id3v1.py#L34

    # and most of the players try to read it. So just adding an mp3 to a player will fetch the whole file
    # setting hacky_handle_mp3_id3v1 will patch reading function so it always return 4096 zero bytes when trying to read block 4096 from an mp3 file inside a zip archive
    zips = [
        (f"{msg.id}_{msg.file.name}", caching.content(msg))
        for msg in messages
        if guards.MessageWithDocument.guard(msg)
        and msg.file.name is not None
        and msg.file.name.endswith(".zip")
    ]

    return {
        "texts": texts,
        "photos": photos,
        "videos": videos,
        "music": music,
        "zips": z.zips_as_dirs(
            dict(zips),
            hacky_handle_mp3_id3v1=True,
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
