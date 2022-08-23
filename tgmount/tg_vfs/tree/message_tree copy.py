from abc import abstractmethod
from typing import Callable, Iterable, Mapping, Protocol, TypedDict, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import vfs
from tgmount.tgclient.guards import MessageDownloadable

from .types import MessagesTree, MessagesTreeValue, Virt
from vfs.map_tree import (
    MapTreeContext,
    TreeMapper,
    is_tree,
    map_tree,
    map_value,
)

# from ..file_factory_mixin import FileFactoryMixin

# from ..mixins import FileFunc

MessagesTreeMapperFunction = TreeMapper[
    MessagesTreeValue,
]


class MessagesTreeMapperProto(Protocol):
    @abstractmethod
    def map_dir(self, ctx: MapTreeContext, dir: Virt.Dir) -> vfs.DirLike:
        ...

    @abstractmethod
    def map_message(self, ctx: MapTreeContext, message: Message) -> vfs.FileLike:
        ...


def messages_tree_mapper(messages_tree_mapper: MessagesTreeMapperProto) -> TreeMapper:
    def _mapper(
        ctx: MapTreeContext,
        tree_value: MessagesTreeValue,
    ):
        return map_messages_tree_value(ctx, messages_tree_mapper, tree_value)

    return _mapper


def map_messages_tree_value(
    ctx: MapTreeContext,
    messages_tree_mapper: MessagesTreeMapperProto,
    tree_value: MessagesTree | MessagesTreeValue,
    # tree_value: MessagesTree | MessagesTreeValue,
) -> vfs.DirContentProto:
    # print(f"walk_messages_tree_value(path={ctx.path}")

    if isinstance(tree_value, Virt.MapContent):
        return tree_value.mapper(
            map_messages_tree_value(
                ctx,
                messages_tree_mapper,
                tree_value.content,
            )
        )

    if isinstance(tree_value, Virt.MapContext):
        return map_messages_tree_value(
            tree_value.mapper(ctx),
            messages_tree_mapper,
            tree_value.tree,
        )

    # if isinstance(tree_value, Virt.MapTree):
    #     return walk_messages_tree_value(
    #         ctx,
    #         messages_tree_walker,
    #         tree_value,
    #     )

    if is_tree(tree_value):
        return vfs.dir_content_from_tree(
            {
                k: map_messages_tree_value(
                    ctx.push_path(k),
                    messages_tree_mapper,
                    v,
                )
                for k, v in tree_value.items()
            }
        )
    # iterable is dir content

    if vfs.DirContentProto.guard(tree_value):
        return tree_value

    # if vfs.FileContentProto.guard(tree_value):
    #     return tree_value

    content = []

    for idx, item in enumerate(tree_value):
        # "Virt.Dir[_T]" | _T
        if isinstance(item, Virt.Dir):
            # Virt.Dir
            content.append(
                messages_tree_mapper.map_dir(
                    ctx.push_path(item.name),
                    item,
                ),
            )
        elif isinstance(item, (vfs.DirLike, vfs.FileLike)):
            content.append(item)
        else:
            # item:  _FT
            content.append(
                messages_tree_mapper.map_message(
                    ctx.push_path(idx),
                    item,
                )
            )

    return vfs.DirContentList(content)


class MessagesTreeMapper(MessagesTreeMapperProto):
    def __init__(self, factory: FileFactoryMixin) -> None:
        self.factory = factory

    def get_file_factory(self, ctx: MapTreeContext) -> FileFactoryMixin:

        factory = ctx.extra.get("file_factory")

        if factory is not None:
            return factory

        return self.factory

    def map_dir(self, ctx: MapTreeContext, dir: Virt.Dir) -> vfs.DirLike:
        # print(f"walk_dir: {ctx} dir.name={dir.name} dir.content={dir.content}")

        content = map_messages_tree_value(
            ctx,
            self,
            dir.content,
        )

        return vfs.DirLike(
            dir.name,
            content,
        )

    def map_message(
        self,
        ctx: MapTreeContext,
        message: MessageDownloadable,
    ) -> vfs.FileLike:
        # print(f"walk_message: {ctx}")
        return self.get_file_factory(ctx).file(message)


class TreeCreator:
    def create_tree(
        self: FileFactoryMixin,
        tree: MessagesTree | MessagesTreeValue,
    ) -> vfs.DirContentSource:

        walker = MessagesTreeMapper(self)

        if is_tree(tree):
            return map_tree(
                tree,
                messages_tree_mapper(walker),
            )

        return map_value(tree, messages_tree_mapper(walker))
