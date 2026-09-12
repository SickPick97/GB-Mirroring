"""Build an isolated Thumb candidate; never writes release firmware or USB."""
import subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'build/emerald-next';out.mkdir(parents=True,exist_ok=True)
 for name in ('resident.c','resident.S','resident.ld','fast.S'):
  source=(ROOT/'firmware/emerald'/name).read_text()
  if name=='fast.S':
   for registers in ('r4','r4,r5','r4-r10'):
    source=source.replace('pop {'+registers+',pc}','pop {'+registers+',lr}\n bx lr')
   for symbol in ('fast_begin','sd_send_fast','hash_begin','scan_next'):
    source=source.replace(symbol+':','.type '+symbol+', %function\n'+symbol+':')
  (out/name).write_text(source)
 tool=sorted(Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi').glob('*/bin/arm-none-eabi-gcc.exe'))[-1]
 common=[str(tool),'-mcpu=arm7tdmi','-mthumb-interwork','-Os','-ffreestanding','-fno-builtin','-nostdlib','-Wall','-Wextra','-Werror']
 for name in ('resident.c','resident.S','fast.S'):
  subprocess.run(common+['-mthumb' if name.endswith('.c') else '-marm','-c',str(out/name),'-o',str(out/(name+'.o'))],check=True)
 subprocess.run(common+['-mthumb','-T'+str(out/'resident.ld'),str(out/'resident.S.o'),str(out/'resident.c.o'),str(out/'fast.S.o'),'-lgcc','-Wl,-Map='+str(out/'resident.map'),'-o',str(out/'resident.elf')],check=True)
 subprocess.run([str(tool.parent/'arm-none-eabi-objcopy.exe'),'-O','binary',str(out/'resident.elf'),str(out/'resident.bin')],check=True)
 from verify_firmware import elf_symbols
 symbols=elf_symbols((out/'resident.elf').read_bytes())
 report=dict(resident_bytes=(out/'resident.bin').stat().st_size,free_before_stack=0x0203f800-symbols['__end__'][0],scope='Build only; requires ARM and emulator validation, no release')
 (out/'build-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
