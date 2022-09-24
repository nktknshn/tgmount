import os
from typing import Mapping
from telethon.tl.custom import Message
from .producers.by_user import group_by_sender
from tgmount.tgclient.message_source import (
    Subscribable,
    TelegramMessageSourceSimple,
)
from tgmount.tgmount.provider_sources import SourcesProvider
from tgmount.util import none_fallback, sets_difference
from tgmount import fs, tgclient, vfs, tglog

from .tgmount_root_producer_types import (
    CreateRootContext,
    ProducerConfig,
    MessagesSet,
    Set,
    TgmountRootSource,
)

from .types import CreateRootResources
from .tgmount_root_config_reader import (
    TgmountConfigReader,
)

from .vfs_tree import UpdateType, VfsTreeDir, VfsTree, VfsTreeSubProto
from .vfs_tree_wrapper import WrapperEmpty, WrapperZipsAsDirs


class VfsTreeProducer:
    def __init__(self, resources: CreateRootResources) -> None:

        self._logger = tglog.getLogger(f"VfsTreeProducer()")

        # self._dir_config = dir_config
        self._resources = resources

    def __repr__(self) -> str:
        return f"VfsTreeProducer()"

    async def produce(
        self, tree_dir: VfsTreeDir | VfsTree, dir_config: TgmountRootSource, ctx=None
    ):
        config_reader = TgmountConfigReader()

        for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            dir_config,
            resources=self._resources,
            ctx=none_fallback(ctx, CreateRootContext.from_resources(self._resources)),
        ):
            # print(f"produce: {vfs.path_join(tree_dir.path, path)}")
            self._logger.info(f"produce: {vfs.path_join(tree_dir.path, path)}")

            if vfs_config.source_dict.get("wrappers") == "ExcludeEmptyDirs":
                # print(vfs_config.source_dict.get("wrappers"))
                sub_dir = await tree_dir.create_dir(path)
                sub_dir._wrappers.append(WrapperEmpty(sub_dir))
            elif vfs_config.source_dict.get("wrappers") == "ZipsAsDirs":
                # print(vfs_config.source_dict.get("wrappers"))
                sub_dir = await tree_dir.create_dir(path)
                sub_dir._wrappers.append(WrapperZipsAsDirs(sub_dir))
            else:
                sub_dir = await tree_dir.create_dir(path)

            if (
                vfs_config.producer_config
                and vfs_config.vfs_producer_name
                and vfs_config.vfs_producer_name == "MessageBySender"
            ):
                producer_arg = none_fallback(vfs_config.vfs_producer_arg, {})
                producer = VfsTreeDirByUser(
                    config=vfs_config.producer_config,
                    dir_cfg=producer_arg.get(
                        "sender_root",
                        VfsTreeDirByUser.DEFAULT_SENDER_ROOT_CONFIG,
                    ),
                    minimum=producer_arg.get("minimum", 1),
                    resources=self._resources,
                    tree_dir=sub_dir,
                )

                sub_dir._subs.append(producer)

                await producer.produce()
            elif vfs_config.producer_config:
                producer = VfsTreePlainDir(sub_dir, vfs_config.producer_config)

                sub_dir._subs.append(producer)

                await producer.produce()


class VfsTreePlainDir(VfsTreeSubProto):
    def __init__(self, dir: VfsTreeDir, config: ProducerConfig) -> None:
        self._config = config
        self._dir = dir

        self._messages = MessagesSet()
        self._message_to_file: dict[str, vfs.FileLike] = {}
        self._logger = tglog.getLogger(f"VfsTreePlainDir({self._dir.path})")

    # @measure_time(logger_func=print)
    async def produce(self):
        self._logger.debug(f"Producing...")

        self._messages = await self._config.get_messages()
        self._message_to_file = {
            m: self._config.factory.file(m) for m in self._messages
        }

        if len(self._message_to_file) > 0:
            await self._dir.put_content(list(self._message_to_file.values()))

        # self._config.message_source.subscribe(self.update)
        self._config.message_source.event_new_messages.subscribe(
            self.update_new_messages
        )

        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

    async def update_new_messages(self, source, new_messages: list[Message]):
        self._logger.info(
            f"update_new_messages({list(map(lambda m: m.id, new_messages))})"
        )

        new_messages = await self._config._apply_filters(new_messages)

        new_files: list[vfs.FileLike] = [
            self._config.factory.file(m) for m in new_messages
        ]

        self._message_to_file.update(
            {
                **{m: f for m, f in zip(new_messages, new_files)},
            }
        )

        if len(new_files):
            await self._dir.put_content(new_files)

    async def update_removed_messages(self, source, removed_messages: list[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )
        removed_files = [self._message_to_file[m] for m in removed_messages]

        for f in removed_files:
            await self._dir.remove_content(f)

    # async def update(self, source, messages: list[Message]):
    #     print(f"updating {self._dir.path}")
    #     messages_set = await self._config.get_messages()

    #     removed_messages, new_messages, common_messages = sets_difference(
    #         self._messages, messages_set
    #     )

    #     removed_files = [self._message_to_file[m] for m in removed_messages]
    #     old_files = [self._message_to_file[m] for m in common_messages]
    #     new_files: list[vfs.FileLike] = [
    #         self._config.factory.file(m) for m in new_messages
    #     ]

    #     self._messages = messages_set
    #     self._message_to_file = {
    #         **{m: f for m, f in zip(new_messages, new_files)},
    #         **{m: f for m, f in zip(common_messages, old_files)},
    #     }

    #     for f in removed_files:
    #         await self._dir.remove_content(f)

    #     if len(new_files):
    #         await self._dir.put_content(new_files)


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
        resources: CreateRootResources,
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
            ctx=CreateRootContext.from_resources(
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


class SourcesProviderMessageSource(
    Subscribable, tgclient.MessageSourceSubscribableProto
):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source
    """

    def __init__(
        self, tree: VfsTree, source: tgclient.MessageSourceSubscribableProto
    ) -> None:
        Subscribable.__init__(self)
        self._source = source
        self._tree = tree

        # self._source.subscribe(self.on_update)
        self._source.event_removed_messages.subscribe(self.removed_messages)
        self._source.event_new_messages.subscribe(self.update_new_message)

        self.updates = Subscribable()
        self.event_new_messages = Subscribable()
        self.event_removed_messages = Subscribable()

        self._logger = tglog.getLogger(f"SourcesProviderMessageSource()")

    async def get_messages(self) -> list[Message]:
        return await self._source.get_messages()

    async def update_new_message(self, source, messages: list[Message]):

        _updates = []

        async def append_update(source, updates: list[UpdateType]):
            _updates.extend(updates)

        self._tree.subscribe(append_update)
        await self.event_new_messages.notify(messages)
        self._tree.unsubscribe(append_update)
        await self.updates.notify(_updates)

    async def removed_messages(self, source, messages: list[Message]):
        self._logger.debug("removed_messages")

        _updates = []

        async def append_update(source, updates: list[UpdateType]):
            _updates.extend(updates)

        self._tree.subscribe(append_update)
        await self.event_removed_messages.notify(messages)
        self._tree.unsubscribe(append_update)
        await self.updates.notify(_updates)


class SourcesProviderAccumulating(SourcesProvider[SourcesProviderMessageSource]):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source before passing them to FS
    """

    MessageSource = SourcesProviderMessageSource

    def __init__(
        self,
        tree: VfsTree,
        source_map: Mapping[str, tgclient.MessageSourceSubscribableProto],
    ) -> None:

        self.updates = Subscribable()
        self._tree = tree

        super().__init__(
            {k: self.MessageSource(self._tree, v) for k, v in source_map.items()}
        )

        for k, v in self._source_map.items():
            v.updates.subscribe(self.updates.notify)
