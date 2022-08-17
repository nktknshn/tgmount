from typing import Callable, Iterable, Mapping, Protocol, TypedDict, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import vfs

from .types import MessagesTree, MessagesTreeValue, Virt
from .walk_tree import (
    WalkTreeContext,
    Mapper as TreeMaper,
    is_tree,
    walk_tree,
    walk_value,
)
from ..file_factory import FileFactoryMixin

# from ..mixins import FileFunc


class MessagesTreeWalkerProto(Protocol):
    def walk_dir(self, ctx: WalkTreeContext, dir: Virt.Dir) -> vfs.DirLike:
        ...

    def walk_message(self, ctx: WalkTreeContext, message: Message) -> vfs.FileLike:
        ...


def messages_tree_walker(messages_tree_walker: MessagesTreeWalkerProto) -> TreeMaper:
    def _mapper(
        ctx: WalkTreeContext,
        tree_value: MessagesTreeValue,
    ):
        return walk_messages_tree_value(ctx, messages_tree_walker, tree_value)

    return _mapper


def walk_messages_tree_value(
    ctx: WalkTreeContext,
    messages_tree_walker: MessagesTreeWalkerProto,
    tree_value: MessagesTree | MessagesTreeValue,
) -> vfs.DirContentProto:
    # print(f"walk_messages_tree_value(path={ctx.path}")

    if isinstance(tree_value, Virt.MapContent):
        return tree_value.mapper(
            walk_messages_tree_value(
                ctx,
                messages_tree_walker,
                tree_value.content,
            )
        )

    if isinstance(tree_value, Virt.MapContext):
        return walk_messages_tree_value(
            tree_value.mapper(ctx),
            messages_tree_walker,
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
                k: walk_messages_tree_value(
                    ctx.push_path(k),
                    messages_tree_walker,
                    v,
                )
                for k, v in tree_value.items()
            }
        )
    # iterable is dir content

    if vfs.DirContentProto.guard(tree_value):
        return tree_value

    content = []

    for idx, item in enumerate(tree_value):
        # "Virt.Dir[_T]" | _T
        if isinstance(item, Virt.Dir):
            # Virt.Dir
            content.append(
                messages_tree_walker.walk_dir(
                    ctx.push_path(item.name),
                    item,
                ),
            )
        elif isinstance(item, (vfs.DirLike, vfs.FileLike)):
            content.append(item)
        else:
            # item:  _FT
            content.append(
                messages_tree_walker.walk_message(
                    ctx.push_path(idx),
                    item,
                )
            )

    return vfs.DirContentList(content)


class MessagesTreeWalker(MessagesTreeWalkerProto):
    def __init__(self, factory: FileFactoryMixin) -> None:
        self.factory = factory

    def get_file_factory(self, ctx: WalkTreeContext) -> FileFactoryMixin:

        factory = ctx.extra.get("file_factory")

        if factory is not None:
            return factory

        return self.factory

    def walk_dir(self, ctx: WalkTreeContext, dir: Virt.Dir) -> vfs.DirLike:
        # print(f"walk_dir: {ctx} dir.name={dir.name} dir.content={dir.content}")

        content = walk_messages_tree_value(
            ctx,
            self,
            dir.content,
        )

        return vfs.DirLike(
            dir.name,
            content,
        )

    def walk_message(self, ctx: WalkTreeContext, message: Message) -> vfs.FileLike:
        # print(f"walk_message: {ctx}")
        return self.get_file_factory(ctx).file(message)


class TreeCreator:
    def create_tree(
        self: FileFactoryMixin, tree: MessagesTree | MessagesTreeValue
    ) -> vfs.DirContentSourceTree | vfs.FsSourceTreeValue:

        walker = MessagesTreeWalker(self)

        if is_tree(tree):
            return walk_tree(
                tree,
                messages_tree_walker(walker),
            )

        return walk_value(tree, messages_tree_walker(walker))
