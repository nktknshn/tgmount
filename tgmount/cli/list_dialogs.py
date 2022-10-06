from telethon.tl.types import User, Channel, Chat
from telethon.utils import get_display_name

from tgmount.tgclient import TgmountTelegramClient


def get_entity_type_str(entity):
    if isinstance(entity, User):
        if entity.bot:
            return "bot"
        return "user"
    if isinstance(entity, Channel):
        if entity.broadcast:
            return "channel"
        return "group"
    if isinstance(entity, Chat):
        return "chat"

    raise ValueError(f"get_entity_type_str(): unknown entity type: {type(entity)}")


def _get_display_name(entity):
    name = get_display_name(entity)
    if isinstance(entity, User) and entity.deleted:
        name = "Deleted Account"
    return name


def _get_username(entity):
    if hasattr(entity, "username") and entity.username is not None:
        return f"@{entity.username}"

    return "<no username>"


async def list_dialogs(
    client: TgmountTelegramClient,
):
    dialogs = await client.get_dialogs()

    for d in sorted(dialogs, key=lambda d: d.date, reverse=True):
        name = _get_display_name(d.entity)

        print(
            f"{get_entity_type_str(d.entity)}\t{d.id}\t{_get_username(d.entity)}\t{name}"
        )
