from .message_tree import MessagesTree, MessagesTreeValue, Virt
from ..file_factory import FileFactoryMixin


def with_filefactory(
    file_factory: FileFactoryMixin,
    d: MessagesTree | MessagesTreeValue,
) -> MessagesTree | MessagesTreeValue:
    return Virt.MapContext(
        lambda ctx: ctx.put_extra("file_factory", file_factory),
        d,
    )


# def with_filefactory_from_ctx(
#     d: MessagesTree | MessagesTreeValue,
# ) -> MessagesTree | MessagesTreeValue:
#     return with_filefactory(
#         lambda ctx, tree: with_filefactory(ctx.extra.get("file_factory"), tree),
#         d,
#     )
