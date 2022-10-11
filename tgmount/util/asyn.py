import asyncio
import os
import threading


async def wait_all(fs) -> list:
    fs = list(map(asyncio.create_task, fs))

    if len(fs) == 0:
        return []

    (done, pending) = await asyncio.wait(fs, return_when=asyncio.ALL_COMPLETED)

    return [d.result() for d in done]


def print_tasks_sync():
    # asyncio.li

    threads = threading.enumerate()

    print(f"Threads: {len(threads)}")

    print(f"Current thread: {threading.current_thread().getName()}")

    for t in threads:
        print(f"{t.getName()}")

    print()

    tasks = list(asyncio.all_tasks())

    print(f"Tasks: {len(tasks)}")

    for t in sorted(tasks, key=lambda t: t.get_name()):
        frame0 = t.get_stack()[0]

        created_at = os.path.basename(frame0.f_code.co_filename)

        print(f"{t.get_name()} -> {t.get_coro()} -> {created_at}")


async def print_tasks():
    print_tasks_sync()
