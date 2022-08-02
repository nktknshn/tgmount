```
TypeMessagesFilter = Union[
    InputMessagesFilterEmpty,
    InputMessagesFilterPhotos,
    InputMessagesFilterVideo,
    InputMessagesFilterPhotoVideo,
    InputMessagesFilterDocument,
    InputMessagesFilterUrl,
    InputMessagesFilterGif,
    InputMessagesFilterVoice,
    InputMessagesFilterMusic,
    InputMessagesFilterChatPhotos,
    InputMessagesFilterPhoneCalls,
    InputMessagesFilterRoundVoice,
    InputMessagesFilterRoundVideo,
    InputMessagesFilterMyMentions,
    InputMessagesFilterGeo,
    InputMessagesFilterContacts,
    InputMessagesFilterPinned
]
```

- The default order is from newest to oldest, but this behaviour can be changed with the `reverse` parameter.

- If either `search`, `filter` or `from_user` are provided,
        :tl:`messages.Search` will be used instead of :tl:`messages.getHistory`.


- limit (`int` | `None`, optional):
    - Due to limitations with the API retrieving more than 3000 messages will take longer than half a minute (or even more based on previous calls).

    - The `limit` may also be `None`, which would eventually return the whole history.

    - Telegram's flood wait limit for :tl:`GetHistoryRequest` seems to be around 30 seconds per 10 requests, therefore a sleep of 1 second is the default for this limit (or above).


- offset_date (`datetime`):
    - Offset date (messages *previous* to this date will be retrieved). Exclusive.

- offset_id
    - Offset message ID (only messages *previous* to the given ID will be retrieved). Exclusive.

- wait_time (`int`):
    