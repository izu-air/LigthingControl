import asyncio

from bleak import BleakScanner


async def main() -> None:
    print("Scanning for 10 seconds...")
    devices = await BleakScanner.discover(timeout=10)
    if not devices:
        print("No BLE devices found.")
        return
    for d in devices:
        print(f"{d.address}  {d.name or '(no name)'}")


if __name__ == "__main__":
    asyncio.run(main())
