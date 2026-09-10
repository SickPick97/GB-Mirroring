"""Offline size study; no USB, no GBA codec implementation or FPS claim."""
from pathlib import Path
import json,struct,zlib,random
ROOT=Path(__file__).resolve().parents[1]
RATE=4328.7

def read_rgb555(path):
    b=path.read_bytes()
    if b[:2]!=b'BM' or struct.unpack_from('<ii',b,18)!=(240,160) or struct.unpack_from('<HHI',b,26)!=(1,24,0):
        raise ValueError('Expected uncompressed bottom-up 240x160 BGR24 BMP')
    offset=struct.unpack_from('<I',b,10)[0]
    if len(b)<offset+240*160*3:raise ValueError('Truncated BMP')
    pixels=[]
    for y in range(159,-1,-1):
        for x in range(240):
            blue,green,red=b[offset+(y*240+x)*3:offset+(y*240+x)*3+3]
            pixels.append((red>>3)|((green>>3)<<5)|((blue>>3)<<10))
    return struct.pack('<38400H',*pixels)

def tiles(data):
    if len(data)!=76800:raise ValueError('Invalid frame size')
    return [b''.join(data[((y+r)*240+x)*2:((y+r)*240+x+8)*2] for r in range(8))
            for y in range(0,160,8) for x in range(0,240,8)]

def study(data,previous=None):
    packed=zlib.compress(data,6)
    assert zlib.decompress(packed)==data
    result=dict(raw_bytes=len(data),zlib_bytes=len(packed),raw_transport_seconds=round(len(data)/RATE,3),
                compressed_transport_seconds=round(len(packed)/RATE,3))
    if previous is not None:
        old=tiles(previous);new=tiles(data)
        delta=b''.join(struct.pack('<H',i)+t for i,t in enumerate(new) if t!=old[i])
        restored=old[:]
        for pos in range(0,len(delta),130):
            index=struct.unpack_from('<H',delta,pos)[0];restored[index]=delta[pos+2:pos+130]
        assert restored==new
        zipped=zlib.compress(delta,6);assert zlib.decompress(zipped)==delta
        result.update(changed_tiles=len(delta)//130,delta_bytes=len(delta),delta_zlib_bytes=len(zipped))
    return result

def main():
    files=sorted((ROOT/'test-results').glob('*/schermo-gba.bmp'))
    rows=[];previous=None
    for f in files:
        data=read_rgb555(f)
        rows.append(dict(source=f.relative_to(ROOT).as_posix(),**study(data,previous)))
        previous=data
    rng=random.Random(123)
    noise=struct.pack('<38400H',*[rng.randrange(32768) for _ in range(38400)])
    report=dict(scope='Offline compression size study, not hardware streaming. Snapshots are different sessions of the same simple homebrew, NOT consecutive game frames.',
                reference_payload_bytes_s=RATE,limitations=['zlib runs on PC here, not on GBA','Timing estimates exclude capture, encoding, framing, acknowledgements and USB delivery','Tile delta requires exact shared base, frame identity and integrity checks before use on wire','No conclusion about Pokemon or other cartridge compression'],
                snapshots=rows,synthetic_noise=study(noise))
    folder=ROOT/'test-results/offline-graphics-study';folder.mkdir(exist_ok=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
