import argparse
import asyncio
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    Optional,
    TypeGuard,
    TypeVar,
    Union,
)

import yaml
from telethon import events, types
from telethon.tl.custom import Message

from tgmount import cache, fs
from tgmount import logging as tglog
from tgmount import main, tg_vfs, tgclient, util, vfs
from tgmount import zip as z
from tgmount.tgclient.guards import *
from tgmount.tgmount import TgmountBase
from tgmount.util import asyn as async_utils
from tgmount.util import func, guards

logger = logging.getLogger("tgvfs")


def get_parser():
    parser = argparse.ArgumentParser()

    # parser.add_argument('--config', 'mount config', required=True)
    parser.add_argument("--id", type=str, default="tgmounttestingchannel")
    parser.add_argument("--debug", type=bool, default=False)
    parser.add_argument("--limit", type=int, default=3000)

    return parser


def organized_with_zips(
    zip_doc_file_factory: tg_vfs.FileFactory,
):
    return tg_vfs.helpers.organized(
        lambda d: tg_vfs.helpers.skip_empty_dirs(
            {
                **d,
                "docs": tg_vfs.with_filefactory(
                    zip_doc_file_factory,
                    tg_vfs.Virt.MapContent(
                        z.zip_as_dir_in_content,
                        d["docs"],
                    ),
                ),
            }
        )
    )


by_user = tg_vfs.helpers.messages_by_user_func(
    lambda by_user, less, nones: [
        *[
            tg_vfs.Virt.Dir(k, organized_with_zips(self.files_factory_cached)(v))
            for k, v in by_user.items()
        ],
        *less,
    ],
)


class Tgmount(TgmountBase):
    """Wrapper for everything yay"""

    def __init__(
        self,
        client: tgclient.TgmountTelegramClient,
        chat_id: str,
        limit: int,
    ) -> None:
        super().__init__(client)

        self._messages: dict[str, list[Message]] = {}
        self._chat_id = chat_id
        self._limit = limit

        self.create_message_sources()

    async def messages_to_fstree(
        self, messages: Iterable[Message]
    ) -> vfs.FsSourceTree | vfs.FsSourceTreeValue:

        return self._files_factory.create_tree(
            {
                "music": tg_vfs.helpers.uniq_docs(
                    filter(MessageWithMusic.guard, messages)
                ),
                "music-alter-names": map(
                    self._files_factory.nfile(
                        lambda msg: f"alter_{msg.id}_{msg.file.performer}_{msg.file.title}{msg.file.ext}"
                        if msg.file.performer
                        else MessageWithMusic.filename(msg)
                    ),
                    filter(MessageWithMusic.guard, messages),
                ),
                "music-by-performer": tg_vfs.helpers.music_by_performer(
                    tg_vfs.helpers.uniq_docs(filter(MessageWithMusic.guard, messages))
                ),
                "organized": organized_with_zips(self.files_factory)(messages),
                "zips-as-dirs": map(
                    z.zip_as_dir,
                    map(
                        self._files_factory_cached.file,
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
                            self.files_factory_cached.file,
                            filter(MessageWithZip.guard, messages),
                        ),
                    )
                ),
                "by-user": await by_user(
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
                ),
            }
        )

    async def create_dir(
        self, messages_source: tgclient.MessageSource
    ) -> vfs.FsSourceTree | vfs.FsSourceTreeValue:

        return await self.messages_to_fstree(
            await messages_source.get_messages(),
        )

    async def update(
        self,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
        messages: list[Message],
    ):
        if self._fs is None:
            return

        await self._fs.update_root(await self.vfs_root())

    def create_message_sources(self):

        self._ms1 = tgclient.MessageSource(
            self._client, chat_id=self._chat_id, limit=self._limit
        )

        self._ms2 = tgclient.MessageSource(
            self._client, chat_id="tgmounttestingchannel", limit=self._limit
        )

        self._ms1.subscribe(self.update)
        self._ms2.subscribe(self.update)

    async def vfs_root(self) -> vfs.VfsRoot:

        vfs_root = vfs.root(
            {
                self._chat_id: await self.create_dir(self._ms1),
                "tgmounttestingchannel": await self.create_dir(self._ms2),
            }
        )

        return vfs_root


async def mount():
    parser = get_parser()
    args = parser.parse_args()

    tglog.init_logging(debug=args.debug)

    client = await main.util.get_tgclient(
        main.util.read_tgapp_api(),
    )

    tgm = Tgmount(
        client,
        chat_id=args.id,
        limit=args.limit,
    )

    await tgm.mount(
        destination="/home/hrn/mnt/tgmount1",
    )


if __name__ == "__main__":
    main.util.run_main(mount)
