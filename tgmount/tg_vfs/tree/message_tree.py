from abc import abstractmethod
from typing import (
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    TypedDict,
    TypeGuard,
    TypeVar,
)

from telethon.tl.custom import Message
from tgmount import vfs
from tgmount.tgclient.guards import MessageDownloadable

from .types import MessagesTree, MessagesTreeValue, MessagesTreeValueDir, Virt
from tgmount.vfs.map_tree import (
    MapTreeContext,
    TreeMapper,
    is_tree,
    map_tree,
    map_value,
)
from ..types import DirContentSourceCreatorProto, FileFactoryProto


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
    ) -> vfs.DirContentProto | vfs.FileContentProto:
        if vfs.FileContentProto.guard(tree_value):
            return tree_value

        return map_value_dir(ctx, messages_tree_mapper, tree_value)

    return _mapper


def map_value_dir(
    ctx: MapTreeContext,
    messages_tree_mapper: MessagesTreeMapperProto,
    tree_value: MessagesTreeValueDir,
) -> vfs.DirContentProto:
    # print(f"walk_messages_tree_value(path={ctx.path}")

    if isinstance(tree_value, Virt.MapContent):
        return tree_value.mapper(
            map_value_dir(
                ctx,
                messages_tree_mapper,
                tree_value.content,
            )
        )

    if isinstance(tree_value, Virt.MapContext):
        return map_value_dir(
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
        return vfs.dir_content_from_source(
            {
                k: map_value_dir(
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
    def __init__(self, factory: FileFactoryProto) -> None:
        self.factory = factory

    def get_file_factory(self, ctx: MapTreeContext) -> FileFactoryProto:

        factory = ctx.extra.get("file_factory")

        if factory is not None:
            return factory

        return self.factory

    def map_dir(self, ctx: MapTreeContext, dir: Virt.Dir) -> vfs.DirLike:
        # print(f"walk_dir: {ctx} dir.name={dir.name} dir.content={dir.content}")

        content = map_value_dir(ctx, self, dir.content)

        return vfs.DirLike(dir.name, content)

    def map_message(
        self,
        ctx: MapTreeContext,
        message: MessageDownloadable,
    ) -> vfs.FileLike:
        treat_as = ctx.extra.get("treat_as", [])
        return self.get_file_factory(ctx).file(message, treat_as=treat_as)


class DirContentSourceCreatorMixin(DirContentSourceCreatorProto):
    def create_dir_content_source(
        self: FileFactoryProto,
        tree: MessagesTree[Message],
        treat_as: Optional[list[str]] = None,
    ) -> vfs.DirContentSource:

        mapper = MessagesTreeMapper(self)

        if is_tree(tree):
            return map_tree(
                tree,
                messages_tree_mapper(mapper),
                extra={"treat_as": treat_as},
            )

        return map_value(
            tree,
            messages_tree_mapper(mapper),
            extra={"treat_as": treat_as},
        )


def create_dir_content_source(
    file_factory: FileFactoryProto,
    tree: MessagesTree[Message],
    treat_as: Optional[list[str]] = None,
) -> vfs.DirContentSource:

    mapper = MessagesTreeMapper(file_factory)

    if is_tree(tree):
        return map_tree(
            tree,
            messages_tree_mapper(mapper),
            extra={"treat_as": treat_as},
        )

    return map_value(
        tree,
        messages_tree_mapper(mapper),
        extra={"treat_as": treat_as},
    )
