import asyncio


async def wait_all(fs) -> list:
    fs = list(map(asyncio.create_task, fs))

    if len(fs) == 0:
        return []

    (done, pending) = await asyncio.wait(fs, return_when=asyncio.ALL_COMPLETED)

    return [d.result() for d in done]
