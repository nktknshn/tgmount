import asyncio
import os
from argparse import ArgumentParser, Namespace
from dataclasses import replace
from typing import Optional

import yaml

from tgmount import config
from tgmount.config import Config, ConfigValidator
from tgmount.config.types import parse_datetime
from tgmount.controlserver import ControlServer
from tgmount.tgclient.client import TgmountTelegramClient
from tgmount.tgclient.fetcher import TelegramMessagesFetcher
from tgmount.tgmount.tgmount_builder import TgmountBuilder
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.tgmount_providers import ProducersProvider
from tgmount.util import int_or_string, yes
from .logger import logger


def add_mount_arguments(command_mount: ArgumentParser):
    command_mount.add_argument("entity", type=str)
    command_mount.add_argument("mount_dir", type=str, metavar="mount-dir")

    command_mount.add_argument(
        "--filter",
        type=str,
        dest="filter",
        choices=list(TelegramMessagesFetcher.FILTERS.keys()),
    )
    command_mount.add_argument("--root-config", type=str, dest="root_config")

    command_mount.add_argument(
        "--producer",
        type=str,
        dest="producer",
        choices=list(ProducersProvider.producers.keys()),
    )

    command_mount.add_argument("--offset-date", type=parse_datetime, dest="offset_date")
    command_mount.add_argument("--offset-id", default=0, type=int, dest="offset_id")
    command_mount.add_argument("--max-id", default=0, type=int, dest="max_id")
    command_mount.add_argument("--min-id", default=0, type=int, dest="min_id")
    command_mount.add_argument("--wait_time", type=float, dest="wait_time")
    command_mount.add_argument("--limit", type=int, dest="limit")

    command_mount.add_argument("--reply-to", type=int, dest="reply_to")
    command_mount.add_argument("--from-user", type=int_or_string, dest="from_user")
    command_mount.add_argument(
        "--reverse", default=False, action="store_true", dest="reverse"
    )
    # command_mount.add_argument(
    #     "--mount-texts", default=False, action="store_true", dest="mount_texts"
    # )
    command_mount.add_argument(
        "--no-updates", default=False, action="store_true", dest="no_updates"
    )

    command_mount.add_argument(
        "--debug-fuse", default=False, action="store_true", dest="debug_fuse"
    )

    command_mount.add_argument("--min-tasks", default=10, type=int, dest="min_tasks")


async def mount(
    args: Namespace,
    *,
    api_credentials: Optional[tuple[int, str]] = None,
    session: Optional[str] = None,
):
    validator = ConfigValidator()
    builder = TgmountBuilder()

    producer = None
    root_content = {
        "source": {"source": args.entity, "recursive": True},
        "filter": "All",
    }

    if yes(args.root_config, str):
        try:
            with open(args.root_config, "r+") as f:
                cfg_dict: dict = yaml.safe_load(f)
                root_content.update(cfg_dict)
        except Exception as e:
            raise TgmountError(f"Error load config file:\n\n{e}")

    if yes(args.producer, str):
        producer = builder.producers.get_by_name(args.producer)

        if producer is None:
            raise TgmountError(f"Invalid producer: {args.producer}")

    if api_credentials is None:
        raise TgmountError(f"Missing api_credentials")

    if session is None:
        raise TgmountError(f"Missing session")

    if yes(producer):
        root_content["producer"] = args.producer

    # logger.debug(f"{root_content}")

    cfg = config.Config(
        client=config.Client(
            session=session,
            api_id=api_credentials[0],
            api_hash=api_credentials[1],
        ),
        message_sources=config.MessageSources(
            sources={
                args.entity: config.MessageSource(
                    entity=args.entity,
                    filter=args.filter,
                    from_user=args.from_user,
                    limit=args.limit,
                    max_id=args.max_id,
                    min_id=args.min_id,
                    offset_date=args.offset_date,
                    offset_id=args.offset_id,
                    reply_to=args.reply_to,
                    reverse=args.reverse,
                    updates=not args.no_updates,
                    wait_time=args.wait_time,
                )
            }
        ),
        root=config.Root(root_content),
    )

    validator.verify_config(cfg)

    tgm = await builder.create_tgmount(cfg)

    try:
        logger.debug(f"Connecting Telegram")
        await tgm.client.auth()
    except Exception as e:
        # await tgm.client.disconnect()
        raise TgmountError(f"Error while authenticating the client: {e}")

    if not tgm.client.is_connected():  # type: ignore
        raise TgmountError(
            f"Error while connecting the client. Check api_id and api_hash"
        )

    await tgm.mount(
        mount_dir=args.mount_dir,
        debug_fuse=args.debug_fuse,
        min_tasks=args.min_tasks,
    )
