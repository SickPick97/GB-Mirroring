"""Pack an RP2040 flash binary into UF2, without flashing any device."""
import argparse
from pathlib import Path
import struct

FLASH_BASE = 0x10000000
FLASH_SIZE = 2 * 1024 * 1024
FAMILY = 0xE48BFF56

def pack(data):
    if not 256 <= len(data) <= FLASH_SIZE:
        raise ValueError('Expected a flash binary between 256 bytes and 2 MiB')
    count = (len(data) + 255) // 256
    result = bytearray()
    for block in range(count):
        payload = data[block*256:(block+1)*256].ljust(256, b'\0')
        result += struct.pack('<8I', 0x0A324655, 0x9E5D5157, 0x2000,
                              FLASH_BASE + block*256, 256, block, count, FAMILY)
        result += payload + bytes(220) + struct.pack('<I', 0x0AB16F30)
    return bytes(result)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('binary', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    result = pack(args.binary.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f'UF2: {args.output} ({len(result)} bytes)')

