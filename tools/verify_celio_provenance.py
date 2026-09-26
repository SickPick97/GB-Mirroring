"""Compare the inherited GBA master PIO words with pinned upstream source."""
import ast,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def number(node):
 if isinstance(node,ast.Constant) and isinstance(node.value,int):return node.value
 if isinstance(node,ast.BinOp) and isinstance(node.op,ast.BitOr):return number(node.left)|number(node.right)
 raise ValueError('Unexpected expression in upstream PIO definition')
def main():
 base=ROOT/'vendor/celio_reference';metadata=json.loads((base/'upstream.json').read_text())
 data=(base/'linkLayer_pio.c').read_bytes()
 assert hashlib.sha256(data).hexdigest()==metadata['sha256']
 section=data.decode().split('RPI_PICO_PIO_DEFINE_PROGRAM(pio_master_gba, 0, 26,',1)[1].split(');',1)[0]
 section=re.sub(r'//[^\n]*','',section)
 for name,value in [('PIO_SC','1'),('PIO_SO','4'),('PIO_SD_GBA','8')]:section=section.replace(name,value)
 expected=[number(ast.parse(x.strip(),mode='eval').body) for x in section.split(',') if x.strip()]
 assert len(expected)==27
 for path,marker in [('firmware/multi-profile/main.c','code[]={'),('firmware/unified/pico.c','boot_code[]={')]:
  source=(ROOT/path).read_text();actual=[int(x,16) for x in source.split(marker,1)[1].split('}',1)[0].split(',')]
  assert actual==expected,path
 print('Celio: all 27 PIO words match pinned upstream in both firmware sources.')
if __name__=='__main__':main()
