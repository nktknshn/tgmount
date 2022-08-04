import logging

import argparse
from telethon import events, types
from telethon.client.updates import EventBuilder

from tgmount import fs, util, vfs
from tgmount import zip as z
from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.logging import init_logging
from tgmount.main.util import mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tgclient import TelegramSearch, TgmountTelegramClient, guards
from tgmount.tgclient.search.filtering.guards import (
    MessageWithCompressedPhoto,
    MessageWithDocumentImage,
)
from tgmount.tgclient.types import Message
from tgmount.vfs import FsSourceTree, text_content
from tgmount.vfs.file import vfile

logger = logging.getLogger("tgvfs")


def get_parser():
    parser = argparse.ArgumentParser()

    # parser.add_argument('--config', 'mount config', required=True)
    parser.add_argument("--id", type=str, default="tgmounttestingchannel")

    return parser


async def tgclient(
    tgapp_api: tuple[int, str],
    session_name="tgfs",
):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client


def print_message(m: Message, verbosity):
    pass


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

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    for msg in messages:
        if guards.MessageWithOtherDocument.guard(msg):
            print(msg)
            print()

    texts = [
        vfile(
            fname=f"{msg.id}.txt",
            content=text_content(msg.message + "\n"),
            creation_time=msg.date,
        )
        for msg in messages
        if guards.MessageWithText.guard(msg)
    ]

    print("zips")
    zips = [caching.file(msg) for msg in messages if guards.MessageWithZip.guard(msg)]

    def fm(guard):
        return [tgfiles.file(msg) for msg in messages if guard(msg)]

    # it's recommended to use cache with zip archives since
    # OS cache will not be applied to the archive file itself

    docs = [
        caching.file(msg)
        for msg in messages
        if guards.MessageWithOtherDocument.guard(msg)
    ]

    photos = fm(
        lambda msg: MessageWithCompressedPhoto.guard(msg)
        or MessageWithDocumentImage.guard(msg)
    )

    videos = fm(guards.MessageWithVideo.guard)
    music = fm(guards.MessageWithMusic.guard)
    voices = fm(guards.MessageWithVoice.guard)
    circles = fm(guards.MessageWithCircle.guard)
    animated = fm(guards.MessageWithAnimated.guard)

    return {
        "animated": animated,
        "stickers": animated,
        # "texts": texts,
        "voices": voices,
        "docs": docs,
        "photos": photos,
        "videos": fm(guards.MessageWithVideoCompressed.guard),
        "all_videos": videos,
        "stickers": fm(guards.MessageWithSticker.guard),
        "circles": circles,
        "music": music,
        "zips": z.zips_as_dirs(
            zips,
            hacky_handle_mp3_id3v1=True,
            skip_folder_if_single_subfolder=True,
        ),
    }


async def mount():
    init_logging(debug=True)
    parser = get_parser()
    args = parser.parse_args()

    client = await tgclient(read_tgapp_api())

    messages_source = client
    documents_source = TelegramFilesSource(client)

    vfs_root = vfs.root(
        {
            "test": await create_test(
                args.id,
                messages_source,
                documents_source,
                client,
                limit=1000,
            ),
        }
    )

    ops = fs.FileSystemOperations(vfs_root)

    await mount_ops(ops, "/home/hrn/mnt/tgmount1")


if __name__ == "__main__":
    run_main(mount)
