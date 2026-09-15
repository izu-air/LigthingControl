from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from .config import ConfigError, load_config
from .controller import build_devices, close_all, connect_all, run_screen_sync, set_color_all, set_power_all

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml", help="path to config.yaml")
    common.add_argument("-v", "--verbose", action="store_true")

    parser = argparse.ArgumentParser(prog="unified-lighting", parents=[common])
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ambilight", parents=[common], help="continuously sync lights to the screen color")

    color_parser = subparsers.add_parser(
        "set-color", parents=[common], help="set a static color on all enabled devices"
    )
    color_parser.add_argument("r", type=int)
    color_parser.add_argument("g", type=int)
    color_parser.add_argument("b", type=int)

    power_parser = subparsers.add_parser("power", parents=[common], help="turn all enabled devices on or off")
    power_parser.add_argument("state", choices=["on", "off"])

    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    devices = build_devices(config)
    await connect_all(devices)

    try:
        if args.command == "set-color":
            for value, label in ((args.r, "r"), (args.g, "g"), (args.b, "b")):
                if not (0 <= value <= 255):
                    print(f"Invalid {label} value: {value} (must be 0-255)", file=sys.stderr)
                    return 1
            await set_color_all(devices, (args.r, args.g, args.b))

        elif args.command == "power":
            await set_power_all(devices, args.state == "on")

        elif args.command == "ambilight":
            stop_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop_event.set)
                except NotImplementedError:
                    pass  # signal handlers are not available on some platforms (e.g. Windows)
            print("Ambilight running, press Ctrl+C to stop...")
            await run_screen_sync(config, devices, stop_event)
    finally:
        await close_all(devices)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.verbose:
        logging.getLogger("unified_lighting").setLevel(logging.DEBUG)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
