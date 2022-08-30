import argparse
import os
from typing import Optional, TypedDict
from tgmount.tgmount import TgmountError

_read_os_env = TypedDict(
    "_read_os_env",
    api_id=Optional[int],
    api_hash=Optional[str],
    session=Optional[str],
)


def parse_tgapp_str(TGAPP: str):
    """format: 111111:ac7e6350d04adeadbeedf1af778773d6f0"""
    try:
        api_id, api_hash = TGAPP.split(":")
        api_id = int(api_id)
    except ValueError:
        raise TgmountError(f"Incorrect value for TGAPP env variable: {TGAPP}")

    return api_id, api_hash


def read_os_env(TGAPP="TGAPP", TGSESSION="TGSESSION") -> _read_os_env:
    TGAPP = os.environ.get(TGAPP)
    TGSESSION = os.environ.get(TGSESSION)

    api_id = None
    api_hash = None

    if TGAPP is not None:
        api_id, api_hash = parse_tgapp_str(TGAPP)

    return _read_os_env(
        api_id=api_id,
        api_hash=api_hash,
        session=TGSESSION,
    )


def get_tgapp_and_session(args: argparse.Namespace):
    os_env = read_os_env()

    api_id = os_env["api_id"]
    api_hash = os_env["api_hash"]
    session = os_env["session"]

    if args.tgapp is not None:
        api_id, api_hash = parse_tgapp_str(args.tgapp)

    if args.session is not None:
        session = args.session

    if session is None or api_id is None or api_hash is None:
        raise TgmountError(f"missing either session or api_id or api_hash")

    return session, api_id, api_hash
