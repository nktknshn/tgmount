import pytest
import pytest_asyncio
from tgmount.tgclient.message_source_types import (
    MessageSourceSubscribableProto,
)
from tgmount.tgclient.message_source_simple import (
    MessageSourceSimple,
)

from tgmount.tgmount.types import Set


class EventsListener:
    def __init__(self, source: MessageSourceSubscribableProto) -> None:
        self.source = source
        self.source.event_new_messages.subscribe(self._on_new_messages)
        self.source.event_removed_messages.subscribe(self._on_removed_messages)

        self.new_messages: list[Set] = []
        self.removed_messages: list[Set] = []

    def reset(self):
        self.new_messages: list[Set] = []
        self.removed_messages: list[Set] = []

    async def _on_new_messages(self, source, messages: Set):
        self.new_messages.append(messages)

    async def _on_removed_messages(self, source, messages: Set):
        self.removed_messages.append(messages)

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        pass


@pytest.mark.asyncio
async def test_simple_source():
    source = MessageSourceSimple[int]()

    async with EventsListener(source) as listener:
        await source.add_messages([1, 2, 3, 4])
        await source.add_messages([4, 5, 6])
        await source.add_messages([4, 5, 6])

        assert listener.new_messages == [{1, 2, 3, 4}, {5, 6}]

        await source.remove_messages([4, 5, 6, 7])
        assert listener.removed_messages == [{4, 5, 6}]
        assert await source.get_messages() == {1, 2, 3}
        listener.reset()

        await source.set_messages(Set({3, 4, 5}))

        assert listener.new_messages == [{4, 5}]
        assert listener.removed_messages == [{1, 2}]
        listener.reset()

        await source.set_messages(Set({3, 4, 5}))
        assert listener.new_messages == []
        assert listener.removed_messages == []
        listener.reset()

        await source.set_messages(Set({1, 2}))
        assert listener.new_messages == [{1, 2}]
        assert listener.removed_messages == [{3, 4, 5}]


@pytest.mark.asyncio
async def test_simple_source_2():
    source = MessageSourceSimple[int]()

    async with EventsListener(source) as listener:
        await source.set_messages(Set({1, 2, 3, 4}))

        assert listener.new_messages == [{1, 2, 3, 4}]
