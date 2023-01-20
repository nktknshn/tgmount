from collections.abc import Sequence
from tgmount.tgclient.message_types import MessageProto
from tgmount.util.col import sets_difference


def messages_difference(
    before: Sequence[MessageProto], after: Sequence[MessageProto]
) -> tuple[
    list[MessageProto],
    list[MessageProto],
    list[tuple[MessageProto, MessageProto]],
]:
    before_dict = {m.id: m for m in before}
    after_dict = {m.id: m for m in after}

    removed, new, common = sets_difference(
        set(before_dict.keys()), set(after_dict.keys())
    )

    return (
        [before_dict[i] for i in removed],
        [after_dict[i] for i in new],
        list(
            zip(
                [before_dict[i] for i in common],
                [after_dict[i] for i in common],
            )
        ),
    )
