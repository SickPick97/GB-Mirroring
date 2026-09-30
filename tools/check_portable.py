"""Offline validation of the portable package, without accessing USB devices."""
import hashlib
import json
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'vendor/celio_transport'))

def main():
    manifest=json.loads((ROOT/'runtime/manifest.json').read_text())
    for relative,expected in manifest.items():
        path=ROOT/'runtime/python'/relative
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Runtime incompleto o modificato: '+relative)
    import mb_multi, usb_link, normal_report, link_bench
    import usb.core, libusb_package
    if libusb_package.get_libusb1_backend() is None:
        raise RuntimeError('Backend USB non disponibile')
    for report,binary,key in [
        ('verifica-emerald-v0.13.1.json','gbmirroring-emerald-v0.13.1.gba','sha256'),
        ('verifica-emerald-v0.13.0.json','gbmirroring-emerald-v0.13.0.gba','sha256'),
        ('verifica-emerald-v0.12.3.json','gbmirroring-emerald-v0.12.3.gba','sha256'),
        ('verifica-emerald-v0.12.2.json','gbmirroring-emerald-v0.12.2.gba','sha256'),
        ('verifica-emerald-v0.12.1.json','gbmirroring-emerald-v0.12.1.gba','sha256'),
        ('verifica-emerald-v0.12.0.json','gbmirroring-emerald-v0.12.0.gba','sha256'),
        ('verifica-emerald-v0.11.0.json','gbmirroring-emerald-v0.11.0.gba','sha256'),
        ('verifica-emerald-v0.10.0.json','gbmirroring-emerald-v0.10.0.gba','sha256'),
        ('verifica-emerald-v0.9.0.json','gbmirroring-emerald-v0.9.0.gba','sha256'),
        ('verifica-emerald-v0.8.0.json','gbmirroring-emerald-v0.8.0.gba','sha256'),
        ('verifica-emerald-v0.7.1.json','gbmirroring-emerald-v0.7.1.gba','sha256'),
        ('verifica-unified-v0.7.0.json','gbmirroring-unified-v0.7.0.uf2','uf2_sha256'),
        ('verifica-emerald-v0.7.0.json','gbmirroring-emerald-v0.7.0.gba','sha256'),
        ('verifica-unified-v0.6.0.json','gbmirroring-unified-v0.6.0.uf2','uf2_sha256'),
        ('verifica-emerald-v0.6.0.json','gbmirroring-emerald-v0.6.0.gba','sha256'),
        ('verifica-emerald-v0.5.1.json','gbmirroring-emerald-v0.5.1.gba','sha256'),
        ('verifica-emerald-v0.5.0.json','gbmirroring-emerald-v0.5.0.gba','sha256'),
        ('verifica-sd-gba-v0.4.2.json','gbmirroring-sd-video-v0.4.2.gba','sha256'),
        ('verifica-sd-gba-v0.4.1.json','gbmirroring-sd-video-v0.4.1.gba','sha256'),
        ('verifica-sd-gba.json','gbmirroring-sd-video-v0.4.0.gba','sha256'),
        ('verifica-sd-pico.json','gbmirroring-sd-video-v0.4.0.uf2','uf2_sha256'),
        ('verifica-multi-profile.json','gbmirroring-multi-profile-v0.3.7.uf2','uf2_sha256'),
        ('verifica-normal-gba.json','gbmirroring-normal-test-v0.3.0.gba','sha256'),
        ('verifica-link-build.json','gbmirroring-link-test-v0.2.0.gba','sha256'),
        ('verifica-normal-pico.json','gbmirroring-normal-test-v0.3.3.uf2','uf2_sha256'),
        ('verifica-firmware.json','gbmirroring-uvc-test-v0.1.0.uf2','uf2_sha256')]:
        expected=json.loads((ROOT/'dist'/report).read_text())[key]
        if hashlib.sha256((ROOT/'dist'/binary).read_bytes()).hexdigest()!=expected:
            raise ValueError('Firmware non corrispondente al manifest: '+binary)
    graphics=json.loads((ROOT/'runtime/mgba/manifest.json').read_text())
    if hashlib.sha256((ROOT/'runtime/mgba/mgba_libretro.dll').read_bytes()).hexdigest()!=graphics['sha256']:
        raise ValueError('Core grafico mGBA incompleto o modificato')
    native=json.loads((ROOT/'runtime/native/manifest.json').read_text())
    if hashlib.sha256((ROOT/'runtime/native/gbm_renderer.dll').read_bytes()).hexdigest()!=native['sha256']:
        raise ValueError('Renderer nativo incompleto o modificato')
    print('Pacchetto GBMirroring', (ROOT/'VERSION').read_text().strip())
    print('OK: runtime, librerie USB, moduli e firmware. Nessun dispositivo interrogato.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('ERRORE:',exc);sys.exit(1)
