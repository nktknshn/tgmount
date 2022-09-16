from telethon.tl.custom import Message


class A:
    def __init__(self, content) -> None:
        self.content = content


print(frozenset([A([1]), A([1, 2])]))
print(Message.__hash__)
