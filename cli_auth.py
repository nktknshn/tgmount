import argparse
from tgmount.main.util import get_tgclient, mount_ops, read_tgapp_api, run_main


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("session_name", type=str)

    return parser


async def main():
    parser = get_parser()
    args = parser.parse_args()

    client = await get_tgclient(
        read_tgapp_api(tgapp_file="tgapp2.txt"),
        session_name=args.session_name,
    )


if __name__ == "__main__":
    run_main(main, forever=True)
