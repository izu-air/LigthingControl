import argparse
import asyncio

from bleak import BleakClient


async def main(mac_address: str, char_uuid: str, hex_bytes: str) -> None:
    payload = bytes.fromhex(hex_bytes.replace(" ", ""))
    print(f"Sending {payload.hex(' ')} to {char_uuid}")
    async with BleakClient(mac_address, timeout=15.0) as client:
        await client.write_gatt_char(char_uuid, payload, response=False)
    print("Sent.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mac_address")
    parser.add_argument("char_uuid")
    parser.add_argument("hex_bytes", help='e.g. "7E 00 05 03 FF 00 00 00 EF"')
    args = parser.parse_args()
    asyncio.run(main(args.mac_address, args.char_uuid, args.hex_bytes))
