"""Check the actual linked descriptors, RP2040 boot image and UF2 container.

No USB access. These checks do not replace enumeration and video tests on a Pico.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

def check(condition, message):
    if not condition: raise ValueError(message)

def elf_symbols(raw):
    check(raw[:6] == b'\x7fELF\x01\x01', 'Expected ELF32 little-endian')
    shoff = struct.unpack_from('<I', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 46)
    sections = [struct.unpack_from('<10I', raw, shoff + stride*i) for i in range(count)]
    symbols = {}
    for sec in sections:
        if sec[1] != 2: continue
        strings_sec = sections[sec[6]]
        strings = raw[strings_sec[4]:strings_sec[4]+strings_sec[5]]
        for off in range(sec[4], sec[4]+sec[5], sec[9]):
            name, value, size, _, _, _ = struct.unpack_from('<IIIBBH', raw, off)
            if name:
                label = strings[name:strings.find(b'\0', name)].decode('utf-8')
                symbols[label] = (value, size)
    return symbols

def verify(binary, elf, uf2):
    data, packed = binary.read_bytes(), uf2.read_bytes()
    check(256 < len(data) <= 2*1024*1024, 'Flash size invalid')
    # Independent MSB-first CRC32 calculation for the first-stage bootloader.
    crc = 0xFFFFFFFF
    for byte in data[:252]:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    check(crc == struct.unpack_from('<I', data, 252)[0], 'Boot2 CRC mismatch')
    sp, reset = struct.unpack_from('<II', data, 256)
    check(0x20000000 < sp <= 0x20042000 and sp % 4 == 0, 'Invalid initial stack')
    check(reset & 1 and 0x10000100 <= (reset & ~1) < 0x10000000+len(data), 'Invalid reset vector')
    check(len(packed) % 512 == 0, 'UF2 size not divisible by 512')
    reconstructed = bytearray()
    count = len(packed)//512
    for i in range(count):
        block = packed[i*512:(i+1)*512]
        m1,m2,flags,addr,size,index,total,family = struct.unpack_from('<8I', block)
        check((m1,m2) == (0x0A324655,0x9E5D5157), 'UF2 header magic')
        check(struct.unpack_from('<I', block,508)[0] == 0x0AB16F30, 'UF2 trailing magic')
        check(flags == 0x2000 and family == 0xE48BFF56, 'Wrong RP2040 family/flags')
        check((addr,size,index,total) == (0x10000000+i*256,256,i,count), 'UF2 address/order/length')
        check(block[288:508] == bytes(220), 'UF2 padding')
        reconstructed += block[32:288]
    check(reconstructed == data.ljust(count*256,b'\0'), 'UF2 payload differs from compiled binary')

    symbols = elf_symbols(elf.read_bytes())
    def read_symbol(name):
        addr, length = symbols[name]
        offset = addr-0x10000000
        check(0 <= offset and offset+length <= len(data), f'{name} outside flash image')
        return data[offset:offset+length]
    dev = read_symbol('gbm_device_descriptor')
    check(len(dev) == 18 and dev[:2] == b'\x12\x01', 'Device descriptor shape')
    check(dev[4:8] == bytes([0xef,2,1,64]), 'Device IAD class/EP0 mismatch')
    vid,pid = struct.unpack_from('<HH',dev,8)
    check((vid,pid) == (0xcafe,0x4020), 'Unexpected test VID/PID')
    cfg = read_symbol('gbm_configuration_descriptor')
    check(cfg[0:2] == b'\x09\x02', 'Configuration descriptor shape')
    check(struct.unpack_from('<H',cfg,2)[0] == len(cfg) and cfg[4] == 2, 'Config total length/interfaces')
    offset, interface = 0, None
    descriptors, interfaces, controls, streams, eps = [], [], [], [], []
    while offset < len(cfg):
        length = cfg[offset]
        check(length >= 2 and offset+length <= len(cfg), 'Truncated USB descriptor')
        d = cfg[offset:offset+length]
        descriptors.append(d)
        if d[1] == 4:
            check(length == 9, 'Interface length')
            interface = d[2]
            interfaces.append((d[2],d[3],d[4],d[5],d[6],d[7]))
        elif d[1] == 0x24:
            (controls if interface == 0 else streams).append(d)
        elif d[1] == 5: eps.append(d)
        offset += length
    check(interfaces == [(0,0,0,14,1,1),(1,0,0,14,2,1),(1,1,1,14,2,1)], 'UVC alt settings')
    check([d[2] for d in controls] == [1,2,3], 'Control descriptor chain')
    check([d[2] for d in streams] == [1,4,5,13], 'Streaming descriptor chain')
    check(struct.unpack_from('<H', controls[0],5)[0] == sum(map(len,controls)), 'VC total')
    check(struct.unpack_from('<H', streams[0],4)[0] == sum(map(len,streams)), 'VS total')
    check(controls[1][3] == controls[2][7] == 1 and controls[2][3] == streams[0][8] == 2,
          'Camera/output/stream terminal chain')
    fmt, frame = streams[1:3]
    check(fmt[5:21] == bytes.fromhex('5955593200001000800000aa00389b71') and fmt[21] == 16, 'YUY2 GUID/bpp')
    width,height = struct.unpack_from('<HH',frame,5)
    min_bps,max_bps,frame_bytes,default = struct.unpack_from('<4I',frame,9)
    intervals = list(struct.unpack_from('<2I',frame,26))
    check((width,height,frame_bytes) == (240,160,76800), 'Video dimensions/buffer')
    check(frame[25] == 2 and intervals == [1000000,2000000] and default == intervals[0], '5/10 fps intervals')
    check((min_bps,max_bps) == (3072000,6144000), 'Video bit rates')
    check(len(eps) == 1 and eps[0][2] == streams[0][6] == 0x81 and eps[0][3] == 5, 'ISO IN endpoint')
    packet = struct.unpack_from('<H',eps[0],4)[0]
    check(packet == 1023 and eps[0][6] == 1, 'Full-speed ISO packet/interval')
    check((packet-2)*1000 > frame_bytes*10, 'Insufficient FS payload capacity')
    check(symbols['frame_buffer'][1] == frame_bytes, 'Linked framebuffer size')
    return dict(status='PASS (static validation; hardware not tested)',
        binary_bytes=len(data),uf2_bytes=len(packed),uf2_blocks=count,
        uf2_sha256=hashlib.sha256(packed).hexdigest(),boot2_crc=hex(crc),
        vid=f'{vid:04X}',pid=f'{pid:04X}',configuration_bytes=len(cfg),
        width=width,height=height,format='YUY2',fps=[10,5],iso_packet_bytes=packet,
        initial_stack=hex(sp),reset_vector=hex(reset))

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build',type=Path,default=Path('build/uvc-test'))
    ap.add_argument('--uf2',type=Path,default=Path('dist/gbmirroring-uvc-test-v0.1.0.uf2'))
    ap.add_argument('--report',type=Path,default=Path('dist/verifica-firmware.json'))
    a=ap.parse_args()
    report=verify(a.build/'gbmirroring_uvc_test.bin',a.build/'gbmirroring_uvc_test.elf',a.uf2)
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
