from telethon.tl.custom import Message

from tgmount import tglog
from tgmount.tgclient.message_source import TelegramMessageSourceSimple
from tgmount.tgmount.producers.by_user import group_by_sender
from tgmount.tgmount.producers.producer_plain import VfsTreePlainDir
from tgmount.tgmount.root_config_types import ReadRootConfigContext
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.tgmount.types import Set
from tgmount.tgmount.vfs_tree import VfsTreeSubProto, VfsTreeDir
from tgmount.tgmount.vfs_tree_producer import VfsTreeProducer
from tgmount.tgmount.vfs_tree_producer_types import ProducerConfig
from tgmount.util import sets_difference


class VfsTreeDirByUser(VfsTreeSubProto):
    MessageSource = TelegramMessageSourceSimple
    DEFAULT_SENDER_ROOT_CONFIG = {"filter": "All"}
    VfsTreeProducer = VfsTreeProducer

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: ProducerConfig,
        *,
        minimum=1,
        resources: TgmountResources,
        dir_cfg=DEFAULT_SENDER_ROOT_CONFIG,
    ) -> None:
        self._config = config
        self._dir = tree_dir

        self._minimum = minimum
        self._resources = resources
        self._dir_cfg = dir_cfg

        self._source_by_name: dict[str, VfsTreeDirByUser.MessageSource] = {}
        self._source_less = self.MessageSource()
        self._logger = tglog.getLogger(f"VfsTreeDirByUser({self._dir.path})")

    async def update_new_message(self, source, messages: list[Message]):
        self._logger.info(f"update_new_messages({list(map(lambda m: m.id, messages))})")

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=1,
        )

        current_dirs = Set(self._source_by_name.keys())

        removed_dirs, new_dirs, common_dirs = sets_difference(
            current_dirs, Set(by_user.keys())
        )

        # for d in removed_dirs:
        #     print(f"VfsTreeDirByUser.removing {d}")
        #     await self._dir.remove_subdir(d)
        #     del self._source_by_name[d]

        for d in new_dirs:
            await self.add_user_dir(d, Set(by_user[d]))

        for d in common_dirs:
            _source = self._source_by_name[d]
            await _source.set_messages(Set(by_user[d]))

    async def update_removed_messages(self, source, removed_messages: list[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        by_user, less, nones = await group_by_sender(
            removed_messages,
            minimum=self._minimum,
        )

        for user_name, user_messages in by_user.items():
            src = self._source_by_name.get(user_name)

            if src is None:
                self._logger.error(f"Missing source for user {user_name}")
                continue

            await src.remove_messages(user_messages)

            if len(await src.get_messages()) == 0:
                await self._dir.remove_subdir(user_name)
                del self._source_by_name[user_name]

    async def add_user_dir(self, user_name: str, user_messages: Set[Message]):
        user_source = self.MessageSource(messages=user_messages)
        user_dir = await self._dir.create_dir(user_name)

        await self.VfsTreeProducer(self._resources).produce(
            user_dir,
            self._dir_cfg,
            ctx=ReadRootConfigContext.from_resources(
                self._resources, recursive_source=user_source
            ),
        )

        self._source_by_name[user_name] = user_source

    # @measure_time(logger_func=print)
    async def produce(self):

        messages = await self._config.get_messages()

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=self._minimum,
        )

        for user_name, user_messages in by_user.items():
            await self.add_user_dir(user_name, Set(user_messages))

        await self._source_less.set_messages(Set(less))

        less_sub = VfsTreePlainDir(
            self._dir, self._config.set_message_source(self._source_less)
        )

        self._dir._subs.append(less_sub)

        await less_sub.produce()

        # self._config.message_source.subscribe(self.update)
        self._config.message_source.event_new_messages.subscribe(
            self.update_new_message
        )
        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

    # async def update(self, source, messages: list[Message]):
    #     messages = await self._config.message_source.get_messages()

    #     by_user, less, nones = await group_by_sender(
    #         messages,
    #         minimum=self._minimum,
    #     )

    #     current_dirs = Set(self._source_by_name.keys())

    #     removed_dirs, new_dirs, common_dirs = sets_difference(
    #         current_dirs, Set(by_user.keys())
    #     )

    #     await self._source_less.set_messages(Set(less))

    #     for d in removed_dirs:
    #         await self._dir.remove_subdir(d)
    #         del self._source_by_name[d]

    #     for d in new_dirs:
    #         await self.add_user_dir(d, Set(by_user[d]))

    #     for d in common_dirs:
    #         _source = self._source_by_name[d]
    #         await _source.set_messages(Set(by_user[d]))
