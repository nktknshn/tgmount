from telethon.tl.types import User, Channel, Chat
from telethon.utils import get_display_name as _get_display_name


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


def get_display_name(entity):
    name = _get_display_name(entity)
    if isinstance(entity, User) and entity.deleted:
        name = "Deleted Account"
    return name


def get_username(entity):
    if hasattr(entity, "username") and entity.username is not None:
        return f"@{entity.username}"

    return "<no username>"
