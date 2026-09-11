"""Read-only local ROM signature check. Does not patch, boot or upload a ROM."""
import argparse,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inspect(data,profile):
 code=data[0xac:0xb0].decode('ascii',errors='replace')
 checks=[]
 for guard in profile['guards']:
  offset=int(guard['address'],16)-0x08000000
  observed=struct.unpack_from('<I',data,offset)[0] if offset+4<=len(data) else None
  checks.append(dict(address=guard['address'],matches=observed==int(guard['expected'],16)))
 return dict(game_code=code,signatures_match=code==profile['game_code'] and all(c['matches'] for c in checks),checks=checks,hook_installation_supported=False)
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('local_dump');args=ap.parse_args()
 result=inspect(Path(args.local_dump).read_bytes(),json.loads((ROOT/'profiles/emerald-it-candidate.json').read_text()))
 print(json.dumps(result,indent=2))
