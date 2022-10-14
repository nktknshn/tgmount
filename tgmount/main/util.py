import asyncio
import logging
import os
import warnings

import pyfuse3
import pyfuse3_asyncio

from tgmount import main
from tgmount.tgclient import TgmountTelegramClient

from tgmount.util.asyn import print_tasks_sync

logger = logging.getLogger("tgvfs")


def read_tgapp_api(tgapp_file="tgapp.txt"):
    if "TGAPP" in os.environ:
        [api, hash] = os.environ["TGAPP"].split(":")

        api_id = int(api)
        api_hash = hash

        return api_id, api_hash

    elif os.path.exists(tgapp_file):
        try:
            with open(tgapp_file, "r") as f:
                [api, hash] = f.read().split(":")

                api_id = int(api)
                api_hash = hash

                return api_id, api_hash
        except Exception:
            raise RuntimeError(f"error reading or parsing {tgapp_file}")

    raise RuntimeError(f"missing TGAPP env variable or {tgapp_file} file")


async def mount_ops(
    fs_ops: pyfuse3.Operations,
    *,
    mount_dir: str,
    min_tasks: int,
    debug=False,
):
    logger.debug("mount_ops()")

    pyfuse3_asyncio.enable()
    # pyfuse3.setxattr(mount_dir, "fuse_stacktrace", b"1")

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add("fsname=test_tgmount")

    if debug:
        fuse_options.add("debug")

    pyfuse3.init(fs_ops, mount_dir, fuse_options)

    main.mounted = True

    await pyfuse3.main(min_tasks=min_tasks)


def run_main(main_func, forever=None, loop=None):

    loop = loop if loop is not None else asyncio.new_event_loop()

    loop.set_debug(True)
    # warnings.simplefilter('always', ResourceWarning)
    # warnings.filterwarnings("error")

    # loop.slow_callback_duration = 0.001

    try:
        loop.run_until_complete(main_func())

        if forever is True or (main.run_forever):
            loop.run_forever()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt")
    except Exception as e:
        # print(str(e))
        # print(str(traceback.format_exc()))
        raise e
    finally:

        if main.mounted:
            pyfuse3.close(unmount=True)

        if main.cleanup:
            main.cleanup()

        if not loop.is_closed():
            loop.close()


async def get_tgclient(
    tgapp_api: tuple[int, str],
    session_name="tgfs",
):
    client = TgmountTelegramClient(session_name, tgapp_api[0], tgapp_api[1])
    await client.auth()
    return client
