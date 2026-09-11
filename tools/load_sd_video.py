"""Load the normal-mode sender, then release Celio for the manual UF2 change."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib
import json
import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/celio_transport'))
sys.path.insert(0,str(ROOT/'tools'))
from link_bench import Log,release

def main():
    folder=ROOT/'dist/sd-video-reports'/datetime.datetime.now().strftime('boot-%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=True)
    link=None
    stdout=sys.stdout
    with (folder/'console.txt').open('w',encoding='utf-8') as f:
        sys.stdout=Log(stdout,f)
        try:
            from usb_link import UsbLink
            from mb_multi import Multiboot
            data=(ROOT/'dist/gbmirroring-sd-video-v0.4.1.gba').read_bytes()
            manifest=json.loads((ROOT/'dist/verifica-sd-gba-v0.4.1.json').read_text())
            if hashlib.sha256(data).hexdigest()!=manifest['sha256']:
                raise RuntimeError('Hash del programma GBA diverso dal manifest')
            print('GBA acceso, slot VUOTO, Pico con firmware Celio. Non premere A sul GBA.')
            link=UsbLink(timing=3700,cable='gba',raw=True)
            link.open()
            result=Multiboot(link,timing_fast=3700,timing_wait=129630,max_attempts=3,detect_s=8).run(data)
            (folder/'multiboot.json').write_text(json.dumps(result,indent=2))
            print('\nMultiboot completato. Sul GBA deve apparire LOAD SD VIDEO UF2.')
            print('LASCIA ACCESO il GBA e NON premere ancora A.')
            print('Ora cambia il firmware Pico con BOOTSEL: gbmirroring-sd-video-v0.4.0.uf2.')
            print('Poi avvia 11-VIDEO-SD.bat. Premi A sul GBA solo quando il PC dice PRONTO.')
            return 0
        except (Exception,SystemExit,KeyboardInterrupt) as exc:
            print('ERRORE:',str(exc) or type(exc).__name__)
            return 1
        finally:
            release(link)
            print('Registro:',folder)
            sys.stdout=stdout

sys.exit(main())
