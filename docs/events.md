```python
def add_event_handler(
        self: 'TelegramClient',
        callback: Callback,
        event: EventBuilder = None):

def remove_event_handler(
        self: 'TelegramClient',
        callback: Callback,
        event: EventBuilder = None) -> int:
```

EventBuilder

Args:

chats (`entity`, optional):
    May be one or more entities (username/peer/etc.), preferably IDs.
    By default, only matching chats will be handled.

blacklist_chats (`bool`, optional):
    Whether to treat the chats as a blacklist instead of
    as a whitelist (default). This means that every chat
    will be handled *except* those specified in ``chats``
    which will be ignored if ``blacklist_chats=True``.

func (`callable`, optional):
    A callable (async or not) function that should accept the event as input
    parameter, and return a value indicating whether the event
    should be dispatched or not (any truthy value will do, it
    does not need to be a `bool`). It works like a custom filter:

    .. code-block:: python

        @client.on(events.NewMessage(func=lambda e: e.is_private))
        async def handler(event):
            pass  # code here