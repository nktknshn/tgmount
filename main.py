import logging

import argparse
from typing import Callable, TypeGuard, TypeVar
from telethon import events, types

from tgmount import fs, vfs
from tgmount import zip as z
from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tg_vfs.mixins import (
    ContentFunc,
    FileContentProvider,
    FileFunc,
    FileFuncSupported,
)
from tgmount.tg_vfs.types import InputSourceItem
from tgmount.tgclient import TelegramSearch, TgmountTelegramClient
from tgmount.tgclient.search.filtering.guards import (
    MessageWithCompressedPhoto,
    MessageWithDocumentImage,
)
from tgmount.tgclient.types import Message
from tgmount.vfs import FsSourceTree
from tgmount.vfs.file import vfile
from tgmount.util import func

from tgmount.tgclient.search.filtering.guards import *

logger = logging.getLogger("tgvfs")


def get_parser():
    parser = argparse.ArgumentParser()

    # parser.add_argument('--config', 'mount config', required=True)
    parser.add_argument("--id", type=str, default="tgmounttestingchannel")
    parser.add_argument("--debug", type=bool, default=False)
    parser.add_argument("--limit", type=int, default=3000)

    return parser


async def tgclient(
    tgapp_api: tuple[int, str],
    session_name="tgfs",
):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


class FileFactory(
    FileFunc,
    ContentFunc,
):
    def __init__(self, files_source: FileContentProvider) -> None:
        self._files_source = files_source

    def file(
        self,
        message: FileFuncSupported | MessageForwarded,
    ) -> vfs.FileLike:

        if MessageForwarded.guard(message) and downloadable(message):
            return vfile(
                f"forward_{FileFunc.filename(self, message)}",
                self.content(message),
            )
        else:
            return FileFunc.file(self, message)

    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:
        return self._files_source.file_content(message, input_item)


T = TypeVar("T")


async def create_test(
    telegram_id: str,
    messages_source: TelegramSearch,
    tgfiles: TelegramFilesSource,
    updates: TgmountTelegramClient,
    limit=1000,
) -> FsSourceTree:
    @updates.on(events.NewMessage(telegram_id))
    async def new_messages_event_handler(
        event: types.UpdateNewMessage | types.UpdateNewChannelMessage,
    ):
        msg = event.message

        if not isinstance(msg, Message):
            return

        print(msg)

    cache = CacheFactoryMemory(blocksize=256 * 1024)
    caching = FilesSourceCaching(tgfiles, cache)

    files = FileFactory(tgfiles)
    cached_files = FileFactory(caching)

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    def fm(guard):
        return [
            files.file(msg) for msg in messages if files.supports(msg) and guard(msg)
        ]

    def f(guard: Callable[[Message], TypeGuard[T]]) -> list[T]:
        return [msg for msg in messages if guard(msg)]

    texts = [
        vfs.text_file(f"{msg.id}.txt", msg.message + "\n", creation_time=msg.date)
        for msg in messages
        if MessageWithText.guard(msg)
    ]

    # it's recommended to use cache with zip archives since
    # OS cache will not be applied to the archive file itself

    zips = [cached_files.file(msg) for msg in messages if MessageWithZip.guard(msg)]

    docs = [files.file(msg) for msg in messages if MessageWithOtherDocument.guard(msg)]

    photos = fm(
        lambda msg: MessageWithCompressedPhoto.guard(msg)
        or MessageWithDocumentImage.guard(msg)
    )

    all_videos = fm(MessageWithVideo.guard)
    music = fm(MessageWithMusic.guard)
    voices = fm(MessageWithVoice.guard)
    circles = fm(MessageWithCircle.guard)
    animated = fm(MessageWithAnimated.guard)

    perf, noperf = MessageWithMusic.group_by_performer(
        f(MessageWithMusic.guard),
        minimum=2,
    )

    fwd = func.walk_values(
        func.cmap(files.file),
        await MessageForwarded.group_by_forw(
            f(lambda m: MessageForwarded.guard(m) and files.supports(m))
        ),
    )

    print(fwd)

    return {
        "animated": animated,
        "forwarded-by-source": fwd,
        "stickers": animated,
        # "texts": texts,
        "voices": voices,
        "docs": docs,
        "photos": photos,
        "videos": fm(MessageWithVideoCompressed.guard),
        "all-videos": all_videos,
        "stickers": fm(MessageWithSticker.guard),
        "circles": circles,
        "music": music,
        "music-by-performer": [
            *[vfs.vdir(perf, map(files.file, tracks)) for perf, tracks in perf.items()],
            *map(files.file, noperf),
        ],
        "zips": z.zips_as_dirs(
            zips,
            hacky_handle_mp3_id3v1=True,
            skip_folder_if_single_subfolder=True,
        ),
    }


async def mount():
    parser = get_parser()
    args = parser.parse_args()

    init_logging(debug=args.debug)

    client = await tgclient(read_tgapp_api())

    messages_source = client
    documents_source = TelegramFilesSource(client)

    vfs_root = vfs.root(
        {
            args.id: await create_test(
                args.id,
                messages_source,
                documents_source,
                client,
                limit=args.limit,
            ),
            "tgmounttestingchannel": await create_test(
                "tgmounttestingchannel",
                messages_source,
                documents_source,
                client,
                limit=args.limit,
            ),
        }
    )

    ops = fs.FileSystemOperations(vfs_root)

    await mount_ops(ops, "/home/hrn/mnt/tgmount1")


if __name__ == "__main__":
    run_main(mount)
