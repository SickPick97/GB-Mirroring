"""Build own experimental resident; no commercial bytes are included."""
import subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 tool=sorted(Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi').glob('*/bin/arm-none-eabi-gcc.exe'))[-1];src=ROOT/'firmware/emerald';out=ROOT/'build/emerald';out.mkdir(exist_ok=True,parents=True)
 font=(ROOT/'firmware/uvc-test/test_pattern.c').read_text().split('static const uint8_t letters',1)[1].split('static void mono_pixel',1)[0];(out/'font.h').write_text('static const uint8_t letters'+font)
 subprocess.run([str(tool),'-mcpu=arm7tdmi','-marm','-Os','-ffreestanding','-fno-builtin','-nostdlib','-Wall','-Wextra','-Werror','-T'+str(src/'resident.ld'),str(src/'resident.S'),str(src/'resident.c'),str(src/'fast.S'),'-lgcc','-Wl,-Map='+str(out/'resident.map'),'-o',str(out/'resident.elf')],check=True)
 subprocess.run([str(tool.parent/'arm-none-eabi-objcopy.exe'),'-O','binary',str(out/'resident.elf'),str(out/'resident.bin')],check=True)
 print('Resident bytes',len((out/'resident.bin').read_bytes()))
 subprocess.run([str(tool),'-mcpu=arm7tdmi','-marm','-nostdlib','-Wl,-Ttext=0x0203fe00',str(src/'stage.S'),'-o',str(out/'stage.elf')],check=True)
 subprocess.run([str(tool.parent/'arm-none-eabi-objcopy.exe'),'-O','binary',str(out/'stage.elf'),str(out/'stage.bin')],check=True)
 assert (out/'stage.bin').stat().st_size<=512
 (out/'blobs.S').write_text('.section .rodata\n.global resident_blob,resident_blob_end,stage_blob,stage_blob_end\nresident_blob:\n.incbin "'+(out/'resident.bin').as_posix()+'"\nresident_blob_end:\nstage_blob:\n.incbin "'+(out/'stage.bin').as_posix()+'"\nstage_blob_end:\n')
 subprocess.run([str(tool),'-mcpu=arm7tdmi','-marm','-Os','-ffreestanding','-fno-builtin','-nostdlib','-Wall','-Wextra','-Werror','-I'+str(out),'-T'+str(ROOT/'firmware/sd-video/gba.ld'),str(ROOT/'firmware/sd-video/start.S'),str(src/'loader.c'),str(out/'blobs.S'),'-lgcc','-o',str(out/'loader.elf')],check=True)
 subprocess.run([str(tool.parent/'arm-none-eabi-objcopy.exe'),'-O','binary',str(out/'loader.elf'),str(out/'loader.bin')],check=True)
 data=bytearray((out/'loader.bin').read_bytes());data[4:0xa0]=(ROOT/'vendor/celio_transport/logo.bin').read_bytes();data[0xa0:0xac]=b'GBMEMERALD  ';data[0xac:0xb0]=b'GBME';data[0xb0:0xbc]=b'00\x96\0\0'+bytes(7);data[0xbc:0xc0]=bytes(4);data[0xbd]=(-sum(data[0xa0:0xbd])-0x19)&255;data.extend(bytes((-len(data))%16))
 (out/'loader.gba').write_bytes(data)
 (ROOT/'dist/gbmirroring-emerald-v0.5.1.gba').write_bytes(data)
 report=dict(status='Experimental; hardware untested',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),resident_bytes=(out/'resident.bin').stat().st_size,scope='Italian BPEI; no scanline effects or UVC; performance unverified')
 (ROOT/'dist/verifica-emerald-v0.5.1.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Loader bytes',len(data))
if __name__=='__main__':main()
