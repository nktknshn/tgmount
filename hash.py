from telethon.tl.custom import Message


class A:
    def __init__(self, id, content) -> None:
        self.id = id
        self.content = content

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"A({self.id}, {self.content})"

    # def __eq__(self, __o: object) -> bool:
    #     return isinstance(__o, A) and self.id == __o.id


old = {A(1, "abc"), A(2, "abc")}

print(A(1, "abcd") in old)
print(old.intersection({A(1, "abcd")}))
