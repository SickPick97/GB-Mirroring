"""Validate host output and decode complete Pico-verified VRAM snapshots."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import json
import struct
import hashlib
import zlib
from link_protocol import bmp

def build_report(folder):
    host=json.loads((folder/'host.json').read_text(encoding='utf-8-sig'))
    results=[];images={};issues=[];done=0
    for line in (folder/'usb.jsonl').read_text(encoding='utf-8-sig').splitlines():
        try:
            obj=json.loads(line)
            if obj['event']=='result': results.append(obj)
            elif obj['event']=='phase_done': done+=1
            elif obj['event']=='error': issues.append(obj)
            elif obj['event']=='image':
                rate=obj['rate'];block=obj['block'];data=bytes.fromhex(obj['hex'])
                if rate not in (262144,2097152) or not 0<=block<300 or len(data)!=256:
                    raise ValueError('Invalid image block')
                parts=images.setdefault(rate,{})
                if block in parts: raise ValueError('Duplicate image block')
                parts[block]=data
        except (ValueError,KeyError,TypeError) as exc:
            issues.append(dict(error=str(exc),line=line[:120]))
    for result in results:
        rate=result['rate']
        elapsed=result['elapsed_us']
        result['payload_bytes_s']=round(result['payload_bytes']*1000000/elapsed,1) if elapsed>0 else 0
        blocks=images.get(rate,{})
        result['image_complete']=False
        if len(blocks)==300 and result['screen_blocks']==75:
            data=b''.join(blocks[i] for i in range(300))
            if zlib.crc32(data)!=result['screen_crc32']:
                issues.append(dict(error='Screenshot CRC32 differs between Pico and PC',rate=rate))
            else:
                target=folder/f'schermo-{rate}.bmp'
                bmp(target,list(struct.unpack('<38400H',data)))
                result['image_complete']=True
                result['image_file']=str(target)
                result['image_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    passed=(host['completed'] and not issues and done==2 and len(results)==2 and
            [r['rate'] for r in results]==[262144,2097152] and
            all(r['clean'] and r['image_complete'] for r in results))
    report=dict(status='PASS' if passed else 'INCOMPLETE_OR_FAILED',host=host,
                phases=results,issues=issues,scope='One-way normal SIO, 1 MiB per rate plus VRAM; no cartridge or UVC')
    (folder/'rapporto.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    r=build_report(Path(sys.argv[1]))
    print('Esito:',r['status'])
    for p in r['phases']:
        print(p['rate'],'Hz:',p['payload_bytes_s'],'B/s; clean=',p['clean'],'immagine completa=',p['image_complete'])
    sys.exit(r['status']!='PASS')
