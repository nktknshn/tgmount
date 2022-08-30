from tgmount.controlserver.server import ControlServer
from tgmount.main.util import run_main


async def main():
    await ControlServer().start()


if __name__ == "__main__":
    run_main(main, forever=True)
