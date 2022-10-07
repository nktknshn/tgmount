from tgmount.tgclient import TgmountTelegramClient
from tgmount.util.tg import get_entity_type_str, get_display_name, get_username


async def list_dialogs(
    client: TgmountTelegramClient,
):
    dialogs = await client.get_dialogs()

    for d in sorted(dialogs, key=lambda d: d.date, reverse=True):
        name = get_display_name(d.entity)

        print(
            f"{get_entity_type_str(d.entity)}\t{d.id}\t{get_username(d.entity)}\t{name}"
        )
