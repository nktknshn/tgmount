from typing import Iterable, TypeVar
from tgmount.util import func
from tgmount.tgclient.guards import (
    MessageDownloadable,
)

T = TypeVar("T", bound=MessageDownloadable)


def uniq_docs(
    messages: Iterable[T],
    picker=lambda v: v[0],
) -> list[T]:
    result = []

    non_downloadable = filter(lambda m: not MessageDownloadable.guard(m), messages)

    for k, v in func.group_by0(
        MessageDownloadable.document_or_photo_id,
        filter(MessageDownloadable.guard, messages),
    ).items():
        if len(v) > 1:
            result.append(picker(v))
        else:
            result.append(v[0])

    return [*result, *non_downloadable]
