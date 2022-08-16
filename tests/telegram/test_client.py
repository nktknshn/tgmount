import os

import pytest
import pytest_asyncio
import tgmount.fs as fs
from telethon import types

from tgmount import vfs, tg_vfs, tgclient
from tgmount.tgclient import TgmountTelegramClient
from ..helpers.fixtures import mnt_dir, tgclient, get_client_with_source

Client = TgmountTelegramClient


# @pytest.mark.asyncio
# async def test_tg1(mnt_dir: str):
#     count = 10
#     storage = tgclient.TelegramFilesSource(tgclient)

#     messages = await tgclient.get_messages_typed(
#         "D1SMBD1D", limit=count, filter=types.InputMessagesFilterMusic
#     )

#     assert len(messages) == count

#     files = []
#     mfs = []

#     for msg in messages:
#         mf = get_music_file(msg)

#         if mf is None:
#             print(msg)
#             continue

#         fc = storage.file_content(mf.message, mf.document)

#         mfs.append((f"{mf.message.chat_id}_{mf.message.id}_{mf.file_name}", mf))
#         files.append((f"{mf.message.chat_id}_{mf.message.id}_{mf.file_name}", fc))

#     assert len(files) == count

#     mf_by_name = dict(mfs)
#     vfs_root = vfs.root(vfs.create_dir_content_from_tree({"D1SMBD1D": dict(files)}))

#     for m in mountfs(str(tmpdir), fs.FileSystemOperations(vfs_root)):
#         subfiles = os.listdir(m.path("D1SMBD1D/"))

#         assert len(subfiles) == count

#         for sf in subfiles:
#             print(mf_by_name[sf])
