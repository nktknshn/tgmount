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

    inputMessagesFilterPhotos - Returns only photos, used for implementing the chat photo gallery, and when scrolling left or right while viewing a photo
    inputMessagesFilterVideo - Returns only videos, used for implementing the chat video gallery, and when scrolling left or right while viewing a video
    inputMessagesFilterPhotoVideo - Return only videos and photos, used for implementing the chat media gallery
    inputMessagesFilterDocument - Return only videos and photos, used for implementing the chat document gallery
    inputMessagesFilterUrl - Return only messages with links, used for implementing the chat link gallery
    inputMessagesFilterGif - Return only GIFs, used for implementing the chat GIF gallery
    inputMessagesFilterVoice - Return only voice messages, used for implementing the chat voice message gallery, and to consecutively play voice messages in a chat
    inputMessagesFilterMusic - Return only music files, used for implementing the chat music gallery
    inputMessagesFilterChatPhotos - Return only chat photos, used to allow scrolling through the profile picture history of a group
    inputMessagesFilterPhoneCalls - Return only phone calls, used with messages.searchGlobal to implement the call tab, with the phone call history
    inputMessagesFilterRoundVoice - Return only round videos and voice messages, used to consecutively play round videos and voice messages in a chat
    inputMessagesFilterRoundVideo - Return only round videos, used to consecutively play round videos in a chat
    inputMessagesFilterMyMentions - Return only messages mentioning me, can be used to display the mention history or, combined with another filter or query, return only messages that satisfy a certain criteria, and contain a mention.
    inputMessagesFilterGeo - Return only geolocations, is used to fetch all recent valid geolocations or live locations sent in a group, to display them all in a single map
    inputMessagesFilterContacts - Return only contacts
    inputMessagesFilterPinned - Returns only pinned messages, used for implementing the pinned message list


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
    