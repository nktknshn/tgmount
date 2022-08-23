import argparse
from pprint import pprint

import yaml

from tgmount import logging, main
from tgmount.config import Config, ConfigValidator
from tgmount.tgmount import TgmountBuilder


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "config", type=str, default="tests/config/config.yaml", nargs="?"
    )
    parser.add_argument("--debug", type=bool, default=False, action="store_false")

    return parser


async def mount():

    args = get_parser().parse_args()

    logging.init_logging(args.debug)

    validator = ConfigValidator()
    builder = TgmountBuilder()

    with open(args.config, "r+") as f:
        cfg_dict: dict = yaml.safe_load(f)

    cfg = Config.from_dict(cfg_dict)

    validator.verify_config(cfg)

    pprint(cfg)

    tgm = await builder.create_tgmount(cfg)

    await tgm.client.auth()

    await tgm.mount()


if __name__ == "__main__":
    main.util.run_main(mount)
