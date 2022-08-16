# from typing import TypedDict
# import pytest
# import pytest_asyncio
# from tgmount.tg_vfs.source import TelegramFilesSource

# from tgmount.tgclient.client import TgmountTelegramClient
# from tgmount.tgclient.search.filtering.guards import MessageWithZip
# from tgmount.tg_vfs._tree.organized import (
#     organized,
#     MessagesTreeHandler,
#     organized_func,
# )
# from tgmount.tg_vfs._tree.by_user import (
#     messages_by_user,
#     messages_by_user_func,
#     messages_by_user_simple,
# )

# from ..helpers.fixtures import tgclient, tgapp_api

# from tgmount.util import func
# from tgmount import zip as z

# Client = TgmountTelegramClient


# @pytest.mark.asyncio
# async def test_orgranized(tgclient: Client):
#     messages = await tgclient.get_messages_typed(
#         "tgmounttestingchannel",
#         limit=100,
#     )

#     tree = MessagesTreeHandler(
#         tgfiles=TelegramFilesSource(tgclient),
#         updates=tgclient,
#     )

#     t = organized(messages)

#     fstree = tree.fstree(t)

#     assert fstree


# class MessagesTreeHandlerZip:
#     pass


# """
# че вообще нужно


# """


# @pytest.mark.asyncio
# async def test_orgranized_2(tgclient: Client):
#     messages = await tgclient.get_messages_typed(
#         "tgmounttestingchannel",
#         limit=100,
#     )

#     tree_handler = MessagesTreeHandler(
#         tgfiles=TelegramFilesSource(tgclient),
#         updates=tgclient,
#     )

#     organized_zips = organized_func(
#         lambda d: {
#             **d,
#             "docs": z.zips_as_dirs(
#                 map(
#                     tree_handler.cached_files.file,
#                     filter(
#                         MessageWithZip.guard,
#                         d["docs"],
#                     ),
#                 )
#             ),
#         }
#     )

#     stree = messages_by_user_simple(
#         lambda by_user, less, nones: {
#             **func.map_values(organized_zips, by_user),
#             "Other": organized_zips(less),
#         }
#     )

#     # by_user = await messages_by_user(
#     #     filter(tree_handler.supports, messages),
#     # )

#     fstree = tree_handler.fstree(
#         await stree(
#             filter(tree_handler.supports, messages),
#         ),
#     )

#     print(fstree)
