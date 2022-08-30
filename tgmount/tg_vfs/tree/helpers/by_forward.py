from tgmount.tgclient.guards import MessageForwarded


@staticmethod
async def group_by_forward(forwarded_messages: list["MessageForwarded"]):
    fws = {}

    for m in forwarded_messages:

        chat = await m.forward.get_chat()
        sender = await m.forward.get_sender()
        from_name = m.forward.from_name

        dirname = (
            chat.title
            if chat is not None
            else from_name
            if from_name is not None
            else "None"
        )

        if not dirname in fws:
            fws[dirname] = []

        fws[dirname].append(m)

    return fws
