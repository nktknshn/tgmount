import os
import pyfuse3
import pyfuse3_asyncio
import logging
import asyncio
import warnings
import traceback

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
    fs_ops: pyfuse3.Operations, destination: str, min_tasks=10, debug=True
):
    logger.debug("mount_ops()")

    # pyfuse3_asyncio_greenback.enable()
    pyfuse3_asyncio.enable()

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add("fsname=test_tgmount")

    # if debug:
    #     fuse_options.add("debug")

    pyfuse3.init(fs_ops, destination, fuse_options)

    await pyfuse3.main(min_tasks=min_tasks)


def run_main(main):
    loop = asyncio.new_event_loop()
    # loop.set_debug(True)
    # warnings.simplefilter('always', ResourceWarning)
    warnings.filterwarnings("error")

    # loop.slow_callback_duration = 0.001

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bye")
    except Exception as e:
        print(str(e))
        print(str(traceback.format_exc()))
    finally:
        # if mounted:
        pyfuse3.close(unmount=True)
