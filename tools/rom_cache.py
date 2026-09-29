"""Local image of the user's own cartridge, used to replay ROM-sourced graphics copies.

The file is read from the cartridge by the GBA (see the dump mode) or supplied by path for
development. It stays on this PC, is never committed and is validated before every use.
"""
import json,os,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'runtime/cache/emerald-bpei.rom'
ROM_SIZE=16*1024*1024
BOOT_CRC=0x6ee38ad1
class RomCacheError(Exception):pass

def validate(data,profile=None):
    """Raise RomCacheError unless data is the Italian Emerald revision the profile describes."""
    import emerald_profile
    if len(data)!=ROM_SIZE:raise RomCacheError('Immagine ROM di %d byte invece di %d'%(len(data),ROM_SIZE))
    profile=profile or json.loads((ROOT/'profiles/emerald-it-candidate.json').read_text())
    if not emerald_profile.inspect(data,profile)['signatures_match']:raise RomCacheError('Immagine ROM diversa da Smeraldo italiano BPEI revisione 0')
    if zlib.crc32(data[:8192])&0xffffffff!=BOOT_CRC:raise RomCacheError('Intestazione ROM diversa dal profilo verificato')
    return data

def path_for(explicit=None):
    return Path(explicit or os.environ.get('GBM_ROM') or DEFAULT)

def load(explicit=None):
    """Return the validated ROM bytes, or None when no local image exists."""
    path=path_for(explicit)
    if not path.is_file():return None
    return validate(path.read_bytes())

def save(data,explicit=None):
    """Validate and atomically store a freshly dumped image."""
    validate(data);path=path_for(explicit);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.part');temporary.write_bytes(data);temporary.replace(path);return path
