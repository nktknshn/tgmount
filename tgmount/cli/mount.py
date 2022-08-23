import os
from argparse import ArgumentParser
from typing import Optional
import yaml

from tgmount.tgclient import TgmountTelegramClient
from tgmount import logging, main
from tgmount.config import Config, ConfigValidator
from tgmount.tgmount import TgmountBuilder
from tgmount.tgmount import TgmountError
from dataclasses import dataclass, replace

from .logger import logger


async def mount(
    config_file: str,
    *,
    api_credentials: Optional[tuple[int, str]] = None,
    session: Optional[str] = None,
    mount_dir: Optional[str] = None,
    debug_fuse=False,
    min_tasks=10,
):
    validator = ConfigValidator()
    builder = TgmountBuilder()

    if not os.path.exists(config_file):
        raise TgmountError(f"Missing config file: {config_file}")

    try:
        with open(config_file, "r+") as f:
            cfg_dict: dict = yaml.safe_load(f)
    except Exception as e:
        raise TgmountError(f"Error load config file:\n\n{e}")

    cfg = Config.from_dict(cfg_dict)

    validator.verify_config(cfg)

    if session is not None:
        cfg.client = replace(cfg.client, session=session)

    if api_credentials is not None:
        logger.info(f"Using api credentials from os enviroment or args")
        cfg.client = replace(
            cfg.client, api_id=api_credentials[0], api_hash=api_credentials[1]
        )

    tgm = await builder.create_tgmount(cfg)

    try:
        await tgm.client.auth()
    except Exception as e:
        await tgm.client.disconnect()
        raise TgmountError(f"Error while authenticating the client: {e}")

    if not tgm.client.is_connected():
        raise TgmountError(
            f"Error while connecting the client. Check api_id and api_hash"
        )

    await tgm.mount(destination=mount_dir, debug_fuse=debug_fuse, min_tasks=min_tasks)


def add_mount_arguments(command_mount: ArgumentParser):
    command_mount.add_argument("config", type=str)
    command_mount.add_argument(
        "--mount-dir", type=str, required=False, dest="mount_dir"
    )
    command_mount.add_argument(
        "--debug-fuse", default=False, action="store_true", dest="debug_fuse"
    )

    command_mount.add_argument("--min-tasks", default=10, type=int, dest="min_tasks")
