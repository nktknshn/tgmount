from .message_tree import MessagesTree, MessagesTreeValue, Virt
from ..file_factory import FileFactory


def with_filefactory(
    file_factory: FileFactory,
    d: MessagesTree | MessagesTreeValue,
) -> MessagesTree | MessagesTreeValue:
    return Virt.MapContext(
        lambda ctx: ctx.put_extra("file_factory", file_factory),
        d,
    )
