from ..types import MessagesTree, MessagesTreeValue, Virt
from tgmount import vfs


async def filter_empty(item: vfs.DirContentItem):

    if vfs.DirLike.guard(item):
        return len(list(await vfs.read_dir_content(item.content))) > 0

    return True


def remove_empty_dirs_content(
    d: vfs.DirContentProto,
) -> vfs.DirContentProto:
    return vfs.filter_dir_content_items(filter_empty, d)


def skip_empty_dirs(
    d: MessagesTree | MessagesTreeValue,
) -> MessagesTree | MessagesTreeValue:
    return Virt.MapContent(remove_empty_dirs_content, d)
