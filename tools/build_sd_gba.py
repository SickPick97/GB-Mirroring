"""Build the cartridge-free ARM7 multiboot image using the local Arm toolchain."""
import hashlib
import argparse
import json
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--normal',action='store_true')
    args=ap.parse_args()
    gcc = shutil.which('arm-none-eabi-gcc')
    if not gcc:
        found = list(Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi').glob('*/bin/arm-none-eabi-gcc.exe'))
        if not found:
            raise SystemExit('Arm GNU Toolchain non trovato.')
        gcc = str(sorted(found)[-1])
    bindir = Path(gcc).parent
    out = ROOT/'build/sd-video-gba'
    out.mkdir(parents=True, exist_ok=True)
    src = ROOT / 'firmware/sd-video'
    c_source=ROOT/'firmware/sd-video/gba.c'
    # Share only our own small font with the already tested UVC firmware.
    font = (ROOT/'firmware/uvc-test/test_pattern.c').read_text().split('static const uint8_t letters',1)[1].split('static void mono_pixel',1)[0]
    (out/'font.h').write_text('static const uint8_t letters'+font)
    elf = out/'gbmirroring-link-test.elf'
    subprocess.run([gcc,'-mcpu=arm7tdmi','-marm','-O2','-ffreestanding','-fno-builtin',
                    '-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                    '-Wall','-Wextra','-Werror','-nostdlib',f'-I{out}',
                    f'-T{src / "gba.ld"}',str(src/'start.S'),str(c_source),str(ROOT/'firmware/sd-video/send.S'),
                    '-lgcc',f'-Wl,-Map={out / "link-test.map"}','-o',str(elf)],check=True)
    raw = out/'link-test.bin'
    subprocess.run([str(bindir/'arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(raw)],check=True)
    data = bytearray(raw.read_bytes())
    # Required BIOS logo bytes from the homebrew header supplied by the user.
    logo = (ROOT/'vendor/celio_transport/logo.bin').read_bytes()
    assert len(logo)==156
    data[4:0xa0] = logo
    data[0xa0:0xac] = b'GBMNORMAL\0\0\0' if args.normal else b'GBMLINKTEST\0'
    data[0xac:0xb0] = b'GBMT'
    data[0xb0:0xbc] = b'00\x96\0\0'+bytes(7)
    data[0xbc:0xc0] = bytes(4)
    data[0xbd] = (-sum(data[0xa0:0xbd])-0x19)&255
    data.extend(bytes((-len(data))%16))
    assert 0x1c0 <= len(data) <= 256*1024
    assert (sum(data[0xa0:0xbe])+0x19)&255 == 0
    assert data[0xc4:0xc6] == bytes(2)
    for offset in (0,0xc0):
        branch, = struct.unpack_from('<I',data,offset)
        target = offset+8+((branch&0xffffff)<<2)
        assert branch>>24 == 0xea and target == 0xe0
    dist = ROOT/'dist'
    dist.mkdir(exist_ok=True)
    result=dist/'gbmirroring-sd-video-v0.4.2.gba'
    result.write_bytes(data)
    report = dict(status='compiled; hardware not tested', bytes=len(data),
                  sha256=hashlib.sha256(data).hexdigest(),load_address='0x02000000',
                  entry_offset='0xC0',start_offset='0xE0',cartridge_access=False)
    (dist/'verifica-sd-gba-v0.4.2.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
