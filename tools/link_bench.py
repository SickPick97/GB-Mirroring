"""Load and measure our cartridge-free GBA program through the supplied Celio.

Original friend modules are imported read-only from vendor/celio_transport.
"""
import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path
from link_protocol import Parser, Measurement, bmp

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'vendor/celio_transport'))

class Log:
    def __init__(self, screen, file):
        self.screen,self.file=screen,file
    def write(self,s):
        self.screen.write(s); self.file.write(s); self.file.flush()
    def flush(self):
        self.screen.flush(); self.file.flush()

def release(link):
    if link is None:
        return
    import usb.util
    link.close()
    if link.dev is not None:
        try:
            link.dev.write(1,b'\x01',timeout=1000)
        except Exception:
            pass
        usb.util.dispose_resources(link.dev)

def load():
    from usb_link import UsbLink
    from mb_multi import Multiboot
    path=ROOT/'dist/gbmirroring-link-test-v0.2.0.gba'
    data=path.read_bytes()
    manifest=json.loads((ROOT/'dist/verifica-link-build.json').read_text())
    if hashlib.sha256(data).hexdigest()!=manifest['sha256']:
        raise RuntimeError('Il file GBA non corrisponde al rapporto di compilazione.')
    print('Multiboot diagnostico: slot VUOTO, GBA acceso. Non inserire cartucce.')
    link=UsbLink(timing=3700,cable='gba',raw=True)
    try:
        link.open()
        mb=Multiboot(link,timing_fast=3700,timing_wait=129630,
                     max_attempts=3,detect_s=8)
        result=mb.run(data)
        print('Multiboot completato. Sul GBA deve comparire GBMIRRORING LINK TEST.')
        print('Riavvio il solo Pico; lascia acceso il GBA.')
        vanished,returned=link.reboot_pico()
        if not (vanished and returned):
            raise RuntimeError('Riavvio Pico non confermato. Lascia acceso il GBA, '
                               'scollega e ricollega solo USB, poi usa 2-MISURA-LINK.bat.')
        return result
    finally:
        release(link)

def receive(link, parser, deadline):
    while time.monotonic()<deadline:
        word=link.read_word(timeout=min(0.1,max(0,deadline-time.monotonic())))
        if word is not None:
            frame=parser.feed(word)
            if frame is not None:
                return frame
    return None

def measure(link, timing, seconds, challenge):
    link.set_timing(timing)
    link.drain_rx(0.6)
    parser=Parser()
    link.send_words([challenge])
    # Synchronize on a complete packet before counting corruption/gaps.
    # Acquisition is bounded even with an absent or nonresponding GBA.
    first=receive(link,parser,time.monotonic()+12)
    if first is None or first[0]!=1:
        return dict(timing=timing,clean=False,error='Nessun pacchetto diagnostico valido entro 12 s')
    baseline=parser.bad_crc
    stats=Measurement(challenge)
    stats.accept(first)
    started=time.monotonic()
    deadline=started+seconds
    next_message=started+5
    while time.monotonic()<deadline:
        frame=receive(link,parser,min(deadline,next_message))
        if frame:
            stats.accept(frame)
        if time.monotonic()>=next_message:
            print(f'  timing {timing}: {stats.frames} pacchetti, CRC errati {parser.bad_crc-baseline}')
            next_message+=5
    # The initial synchronization packet is excluded from the byte-rate numerator.
    result=stats.result(time.monotonic()-started,parser.bad_crc-baseline)
    result['verified_payload_bytes_s']=round(max(0,stats.frames-1)*128/result['seconds'],1)
    result['timing']=timing
    print(json.dumps(result,ensure_ascii=False))
    return result

def screenshot(link, timing, folder):
    print('Cattura VRAM: lo schermo GBA resta fermo durante il trasferimento.')
    link.set_timing(timing)
    link.drain_rx(0.6)
    parser=Parser()
    link.send_words([0xc001])
    chunks={}
    start=time.monotonic()
    deadline=start+360
    last_progress=start
    last_packet=start
    while time.monotonic()<deadline:
        frame=receive(link,parser,min(deadline,time.monotonic()+1))
        if frame and frame[0]==2:
            _,index,data=frame
            if index>=600:
                raise RuntimeError('Indice screenshot non valido')
            if index in chunks and chunks[index]!=data:
                raise RuntimeError('Blocco screenshot duplicato e discordante')
            chunks[index]=data
            last_packet=time.monotonic()
            if len(chunks)==600:
                pixels=[v for i in range(600) for v in chunks[i]]
                path=folder/'schermo-gba.bmp'
                bmp(path,pixels)
                print(f'Immagine completa ricevuta dal GBA: {path}')
                return dict(complete=True,blocks=600,crc_errors=parser.bad_crc,
                            seconds=round(time.monotonic()-start,2),file=str(path),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        elif frame and frame[0]==1 and chunks:
            break
        now=time.monotonic()
        if now-last_progress>=5:
            print(f'  Screenshot: {len(chunks)}/600 blocchi ricevuti')
            last_progress=now
        if now-last_packet>15:
            break
    return dict(complete=False,blocks=len(chunks),crc_errors=parser.bad_crc,
                error='Cattura incompleta: nessuna immagine parziale presentata come completa')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skip-boot',action='store_true')
    ap.add_argument('--seconds',type=int,default=20)
    ap.add_argument('--no-screenshot',action='store_true')
    args=ap.parse_args()
    if not 15<=args.seconds<=300:
        ap.error('--seconds deve essere fra 15 e 300')
    folder=ROOT/'dist/link-reports'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    report=dict(status='INCOMPLETE',phases=[],hardware_test=True,
                description='Celio multiplayer baseline; not normal-mode bandwidth or cartridge capture')
    link=None
    original_out,original_err=sys.stdout,sys.stderr
    with (folder/'console.txt').open('w',encoding='utf-8') as logfile:
        sys.stdout=Log(original_out,logfile)
        sys.stderr=Log(original_err,logfile)
        try:
            from usb_link import UsbLink
            if not args.skip_boot:
                report['multiboot']=load()
            print('Avvio misura. Puoi premere A/B sul GBA: i tasti sono inclusi nei dati.')
            link=UsbLink(timing=7400,cable='gba',raw=True)
            link.open()
            for index,timing in enumerate([7400,3700,2000,1000,500]):
                r=measure(link,timing,args.seconds,0xd120+index)
                report['phases'].append(r)
                if not r.get('clean'):
                    print('Fase non pulita: fermo la salita di velocita e conservo i risultati.')
                    break
            clean=[r for r in report['phases'] if r.get('clean')]
            if clean:
                best=max(clean,key=lambda r:r['verified_payload_bytes_s'])
                report['best_measured']=best
                if not args.no_screenshot:
                    # One step slower than best for the longer full-screen transfer.
                    capture=clean[max(0,clean.index(best)-1)]
                    report['screenshot']=screenshot(link,capture['timing'],folder)
                all_clean=all(r.get('clean') for r in report['phases'])
                image_ok=args.no_screenshot or report['screenshot']['complete']
                report['status']='PASS' if all_clean and image_ok else 'PARTIAL'
            else:
                report['status']='FAIL'
        except (Exception,SystemExit,KeyboardInterrupt) as exc:
            report['status']='ERROR'
            report['error']=str(exc) or type(exc).__name__
            print('Prova interrotta:',report['error'])
        finally:
            release(link)
            (folder/'rapporto.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            print(f'Esito: {report["status"]}. Rapporto: {folder}')
            print('Ora puoi spegnere il GBA. Questo test non richiede cartucce.')
            sys.stdout,sys.stderr=original_out,original_err
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    sys.exit(main())
