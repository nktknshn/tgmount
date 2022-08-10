from typing import Iterable
from tgmount.util import func
from tgmount.tgclient import MessageDownloadable, document_or_photo_id


def uniq_docs(
    messages: Iterable[MessageDownloadable],
    picker=lambda v: v[0],
):
    result = []
    for k, v in func.group_by0(document_or_photo_id, messages).items():
        if len(v) > 1:
            result.append(picker(v))
        else:
            result.append(v[0])

    return result
