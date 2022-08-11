from typing import Callable, TypedDict, TypeGuard, TypeVar, Union

from telethon.tl.custom import Message
from tgmount.tg_vfs._tree.types import MessagesTree, MessagesTreeValue
from tgmount.tgclient.search.filtering.guards import *
from tgmount.tgclient.search.filtering.guards import (
    MessageWithCompressedPhoto,
    MessageWithDocumentImage,
)

from .music import music_by_performer

T = TypeVar("T")


OrganizedTree = TypedDict(
    "OrganizedTree",
    music=Iterable[MessageWithMusic],
    music_by_performer=MessagesTreeValue[MessageWithMusic],
    videos=Iterable[MessageWithVideoCompressed],
    animated=Iterable[MessageWithAnimated],
    voices=Iterable[MessageWithVoice],
    docs=Iterable[MessageWithOtherDocument],
    photos=Iterable[MessageWithCompressedPhoto | MessageWithDocumentImage],
    stickers=Iterable[MessageWithSticker],
    circles=Iterable[MessageWithCircle],
    all_videos=Iterable[MessageWithVideo],
)


def organize_messages(
    messages: Iterable[Message], *, music_by_performer_minimum=2
) -> OrganizedTree:
    def f(guard: Callable[[Message], TypeGuard[T]]) -> Iterable[T]:
        return filter(guard, messages)

    return {
        "music": f(MessageWithMusic.guard),
        "music_by_performer": music_by_performer(
            f(MessageWithMusic.guard),
            minimum=music_by_performer_minimum,
        ),
        "videos": f(MessageWithVideoCompressed.guard),
        "animated": f(MessageWithAnimated.guard),
        "voices": f(MessageWithVoice.guard),
        "docs": f(MessageWithOtherDocument.guard),
        "photos": [
            *f(MessageWithCompressedPhoto.guard),
            *f(MessageWithDocumentImage.guard),
        ],
        "stickers": f(MessageWithSticker.guard),
        "circles": f(MessageWithCircle.guard),
        "all_videos": f(MessageWithVideo.guard),
    }


def organized(
    func: Callable[[OrganizedTree], MessagesTree[T] | MessagesTreeValue[T]],
    *,
    music_by_performer_minimum=2
):
    def _inner(
        messages: Iterable[Message],
    ):
        return func(
            organize_messages(
                messages,
                music_by_performer_minimum=music_by_performer_minimum,
            )
        )

    return _inner
