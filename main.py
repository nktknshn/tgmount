import argparse

import yaml

from tgmount.config import Config, ConfigValidator
from tgmount.tgmount.builder import TgmountBuilder
from tgmount import main
from tgmount import logging

from pprint import pprint


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("config", type=str, default="tests/config/config.yaml")
    parser.add_argument("--debug", type=bool, default=False)

    return parser


async def mount():
    logging.init_logging(True)

    validator = ConfigValidator()

    args = dict(config="tests/config/config.yaml")

    with open(args["config"], "r+") as f:
        cfg_dict: dict = yaml.safe_load(f)

    cfg = Config.from_dict(cfg_dict)

    validator.verify_config(cfg)

    pprint(cfg)

    builder = TgmountBuilder()

    tgm = await builder.create_tgmount(cfg)

    await tgm.client.auth()

    await tgm.mount()


if __name__ == "__main__":
    main.util.run_main(mount)
