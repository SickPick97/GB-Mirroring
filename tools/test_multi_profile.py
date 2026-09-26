"""Execute extracted, unmodified C packet validator as ARM code with mocked time."""
import sys,struct,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_LR,UC_ARM_REG_SP
from link_protocol import crc,pattern
from verify_firmware import elf_symbols
out=ROOT/'build/multi-validator';out.mkdir(exist_ok=True)
source=(ROOT/'firmware/multi-profile/main.c').read_text()
# Check exact inherited PIO sequence against the reference used for this port.
import re
reference=(ROOT/'vendor/celio_reference/linkLayer_pio.c').read_text()
section=reference.split('RPI_PICO_PIO_DEFINE_PROGRAM(pio_master_gba, 0, 26,',1)[1].split(');',1)[0]
section=re.sub(r'//[^\n]*','',section)
for name,value in [('PIO_SC','1'),('PIO_SO','4'),('PIO_SD_GBA','8')]:section=section.replace(name,value)
expected=[eval(x.strip(),{'__builtins__':{}},{}) for x in section.split(',') if x.strip()]
actual=[int(x,16) for x in source.split('code[]={',1)[1].split('}',1)[0].split(',')]
assert actual==expected and len(actual)==27
state=source[source.index('static uint16_t packet'):source.index('static void output')]
stub='#include <stdint.h>\n#include <stddef.h>\nuint64_t clock_value; uint64_t time_us_64(void){return ++clock_value;}\nvoid *memmove(void *d,const void *s,size_t n){char *a=d;const char*b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}\n'
entry='\nunsigned validate(uint16_t *p,unsigned count){for(unsigned i=0;i<count;i++)feed(p[i]);return frames | (bad_crc<<8) | (bad_pattern<<16) | (gaps<<24);}\n'
(out/'test.c').write_text(stub+state+entry)
gcc=next(Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi').glob('*/bin/arm-none-eabi-gcc.exe'))
subprocess.run([str(gcc),'-mcpu=arm7tdmi','-marm','-O2','-nostdlib','-ffreestanding','-fno-builtin','-Wl,-Ttext=0x02000000','-Wl,-e,validate',str(out/'test.c'),'-o',str(out/'test.elf')],check=True)
subprocess.run([str(gcc.parent/'arm-none-eabi-objcopy.exe'),'-O','binary',str(out/'test.elf'),str(out/'test.bin')],check=True)
symbols=elf_symbols((out/'test.elf').read_bytes())
def packet(seq):
 data=[0xd160,0,0,0,0,0,0]+[pattern(seq,i) for i in range(7,64)]
 w=[0xb17e,0x4d47,1,1,seq,0,64]+data
 return w+[crc(w[2:])]
def execute(words):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x02000000,0x40000)
 u.mem_write(0x02000000,(out/'test.bin').read_bytes());u.mem_write(0x02020000,struct.pack('<'+'H'*len(words),*words))
 u.reg_write(UC_ARM_REG_R0,0x02020000);u.reg_write(UC_ARM_REG_R1,len(words));u.reg_write(UC_ARM_REG_SP,0x0203fff0);u.reg_write(UC_ARM_REG_LR,0x0203f000)
 u.emu_start(symbols['validate'][0],0x0203f000,count=2000000)
 return u.reg_read(UC_ARM_REG_R0)
assert execute(packet(0)+packet(1))==2
bad=packet(0);bad[-1]^=1
assert execute(bad+packet(1))==257
assert execute(packet(0)+packet(2))==(2|(1<<24))
bad=packet(0);bad[20]^=1;bad[-1]=crc(bad[2:-1])
assert execute(bad)==(1|(1<<16))
assert execute([0,123,65535]+packet(0))==1
report=dict(passed=True,cases=5,scope='Actual C validator ARM execution with mocked timer; no PIO electrical, USB or hardware timing test')
(ROOT/'dist/verifica-multi-validator.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
