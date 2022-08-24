from ..types import MessagesTree, MessagesTreeValue, MessagesTreeValueDir, Virt
from tgmount import vfs


async def filter_empty(item: vfs.DirContentItem):

    if vfs.DirLike.guard(item):
        return len(list(await vfs.dir_content_read(item.content))) > 0

    return True


def remove_empty_dirs_content(
    d: vfs.DirContentProto,
) -> vfs.DirContentProto:
    return vfs.dir_content_filter_items(filter_empty, d)


def skip_empty_dirs(
    d: MessagesTreeValueDir,
) -> MessagesTreeValueDir:
    return Virt.MapContent(remove_empty_dirs_content, d)
