import argparse
import asyncio

from bleak import BleakClient


async def main(mac_address: str) -> None:
    async with BleakClient(mac_address, timeout=15.0) as client:
        print(f"Connected to {mac_address}\n")
        for service in client.services:
            print(f"Service {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic {char.uuid}  properties={char.properties}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mac_address")
    args = parser.parse_args()
    asyncio.run(main(args.mac_address))
