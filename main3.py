import argparse
import asyncio
import logging
from typing import Any, Callable, Iterable, TypeGuard, TypeVar, Union

from telethon import events, types
from telethon.tl.custom import Message
from typing_extensions import reveal_type

from tgmount import fs, vfs
from tgmount import zip as z
from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.logging import init_logging
from tgmount.main.util import get_tgclient, mount_ops, read_tgapp_api, run_main
from tgmount.tg_vfs import TelegramFilesSource, helpers
from tgmount.tg_vfs._tree.types import MessagesTreeValue, Virt
from tgmount.tg_vfs.helpers.organized import organize_messages
from tgmount.tg_vfs.tree import FileFactory
from tgmount.tgclient import (
    MessageDownloadable,
    MessageWithCompressedPhoto,
    MessageWithDocumentImage,
    MessageWithMusic,
    MessageWithZip,
    TelegramSearch,
    TgmountTelegramClient,
    document_or_photo_id,
)
from tgmount.tgclient.search.filtering.guards import (
    MessageWithOtherDocument,
    MessageWithVideo,
    MessageWithVoice,
)
from tgmount.util import asyn as async_utils
from tgmount.util import func
from tgmount.vfs import FsSourceTree
from tgmount.vfs.file import vfile

logger = logging.getLogger("tgvfs")
T = TypeVar("T")


def guards(*gs: Callable[[Message], TypeGuard[Any]]) -> Callable[[Message], bool]:
    return lambda m: any(map(lambda g: g(m), gs))


def get_parser():
    parser = argparse.ArgumentParser()

    # parser.add_argument('--config', 'mount config', required=True)
    parser.add_argument("--id", type=str, default="tgmounttestingchannel")
    parser.add_argument("--debug", type=bool, default=False)
    parser.add_argument("--limit", type=int, default=3000)

    return parser


async def create_test(
    telegram_id: str,
    messages_source: TelegramSearch,
    tgfiles: TelegramFilesSource,
    updates: TgmountTelegramClient,
    limit=1000,
) -> FsSourceTree:

    caching = FilesSourceCaching(
        tgfiles,
        document_cache_factory=CacheFactoryMemory(blocksize=256 * 1024),
    )

    files = FileFactory(tgfiles)
    cached_files = FileFactory(caching)

    messages = await messages_source.get_messages_typed(
        telegram_id,
        limit=limit,
    )

    organized_with_zips = helpers.organized(
        lambda d: {
            "music_by_performer": d["music_by_performer"],
            "docs": Virt.MapContext(
                lambda ctx: ctx.put_extra("file_factory", cached_files),
                Virt.MapContent(
                    z.zip_as_dir_in_content,
                    d["docs"],
                ),
            ),
            "all_videos": d["all_videos"],
            "voices": d["voices"],
        }
    )

    by_user = helpers.messages_by_user_func(
        lambda by_user, less, nones: [
            *[Virt.Dir(k, organized_with_zips(v)) for k, v in by_user.items()],
            *less,
        ],
    )

    return {
        "music": map(
            files.file, helpers.uniq_docs(filter(MessageWithMusic.guard, messages))
        ),
        "music-alter-names": map(
            files.nfile(
                lambda msg: f"{msg.id}_{msg.file.performer}_{msg.file.title}{msg.file.ext}"
                if msg.file.performer
                else MessageWithMusic.filename(msg)
            ),
            filter(MessageWithMusic.guard, messages),
        ),
        "music-by-performer": files.create_tree(
            helpers.music_by_performer(
                helpers.uniq_docs(filter(MessageWithMusic.guard, messages))
            )
        ),
        "organized": files.create_tree(organized_with_zips(messages)),
        "zips-as-dirs": map(
            z.zip_as_dir,
            map(
                cached_files.file,
                filter(MessageWithZip.guard, messages),
            ),
        ),
        "zips-single": await async_utils.wait_all(
            map(
                z.zip_as_dir_s(
                    skip_folder_if_single_subfolder=True,
                    skip_folder_prefix=1,
                ),
                map(
                    cached_files.file,
                    filter(MessageWithZip.guard, messages),
                ),
            )
        ),
        "by-user": files.create_tree(
            await by_user(
                filter(
                    guards(
                        MessageWithMusic.guard,
                        MessageWithOtherDocument.guard,
                        MessageWithVideo.guard,
                        MessageWithVoice.guard,
                    ),
                    messages,
                ),
                minimum=2,
            )
        ),
    }


async def mount():
    parser = get_parser()
    args = parser.parse_args()

    init_logging(debug=args.debug)

    client = await get_tgclient(read_tgapp_api())

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
