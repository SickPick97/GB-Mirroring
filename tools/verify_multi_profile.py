"""Independent UF2/boot checks and linked CDC/DMA layout verification."""
import hashlib
import json
import struct
from pathlib import Path
from verify_firmware import elf_symbols, check
ROOT=Path(__file__).resolve().parents[1]

def verify():
    binary=(ROOT/'build/uvc-test/gbmirroring_multi_profile.bin').read_bytes()
    uf2=(ROOT/'dist/gbmirroring-multi-profile-v0.3.6.uf2').read_bytes()
    symbols=elf_symbols((ROOT/'build/uvc-test/gbmirroring_multi_profile.elf').read_bytes())
    crc=0xffffffff
    for b in binary[:252]:
        crc ^= b<<24
        for _ in range(8): crc=((crc<<1)^(0x04c11db7 if crc&0x80000000 else 0))&0xffffffff
    check(crc==struct.unpack_from('<I',binary,252)[0],'Boot2 CRC')
    sp,pc=struct.unpack_from('<II',binary,256)
    check(0x20000000<sp<=0x20042000 and pc&1 and 0x10000100<pc<0x10000000+len(binary),'Boot vectors')
    check(len(uf2)%512==0,'UF2 length')
    count=len(uf2)//512
    raw=bytearray()
    for i in range(count):
        block=uf2[i*512:(i+1)*512]
        check(struct.unpack_from('<8I',block)==(0x0a324655,0x9e5d5157,0x2000,0x10000000+i*256,256,i,count,0xe48bff56),'UF2 block header')
        check(struct.unpack_from('<I',block,508)[0]==0x0ab16f30,'UF2 trailer')
        raw.extend(block[32:288])
    check(raw==binary.ljust(count*256,b'\0'),'UF2 roundtrip')
    def symbol(name):
        address,size=symbols[name]
        return binary[address-0x10000000:address-0x10000000+size]
    dev=symbol('normal_device_descriptor')
    check(len(dev)==18 and struct.unpack_from('<HH',dev,8)==(0xcafe,0x4022),'CDC VID/PID')
    config=symbol('normal_configuration_descriptor')
    check(struct.unpack_from('<H',config,2)[0]==len(config) and config[4]==2,'Config length')
    pos=0;interfaces=[];endpoints=[]
    while pos<len(config):
        n,t=config[pos:pos+2];check(n>=2 and pos+n<=len(config),'Descriptor framing')
        d=config[pos:pos+n]
        if t==4: interfaces.append((d[2],d[5]))
        if t==5: endpoints.append((d[2],d[3],struct.unpack_from('<H',d,4)[0]))
        pos+=n
    check(interfaces==[(0,2),(1,10)],'CDC interface classes')
    check(endpoints==[(0x81,3,8),(2,2,64),(0x82,2,64)],'CDC endpoint layout')
    report=dict(status='PASS static; hardware untested',uf2_sha256=hashlib.sha256(uf2).hexdigest(),
                binary_bytes=len(binary),uf2_bytes=len(uf2),usb='CAFE:4022 CDC')
    (ROOT/'dist/verifica-multi-profile.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__': print(json.dumps(verify(),indent=2))
