"""Immutable graphics dependencies for the next transport (not yet on GBA).

No presentation is allowed with missing or overwritten resource versions.
Keys here are host-side content identities, not the final Link wire encoding.
"""
import hashlib
from collections import OrderedDict, deque
from dataclasses import dataclass

BLOCK_SIZE = 256
VRAM_BLOCKS = 384
HOT_SIZE = 2304

def identity(data):
    if len(data) != BLOCK_SIZE:
        raise ValueError('A resource must contain exactly 256 bytes')
    return hashlib.sha256(data).digest()

@dataclass(frozen=True)
class State:
    epoch: int
    sequence: int
    game_frame: int
    hot: bytes
    resources: tuple

    def __post_init__(self):
        if len(self.hot) != HOT_SIZE or len(self.resources) != VRAM_BLOCKS:
            raise ValueError('Incomplete state dependencies')
        if any(type(key) is not bytes or len(key) != 32 for key in self.resources):
            raise ValueError('Invalid resource identity')
        if type(self.hot) is not bytes or type(self.resources) is not tuple:
            raise ValueError('State must own immutable memory')
        if any(type(n) is not int or not 0 <= n <= 0xffffffff
               for n in (self.epoch, self.sequence, self.game_frame)):
            raise ValueError('Invalid state timestamp or epoch')

class Resources:
    def __init__(self, capacity=16384, pending_limit=16):
        if capacity < VRAM_BLOCKS or not 0 < pending_limit <= 64:
            raise ValueError('Invalid cache bounds')
        self.capacity=capacity;self.pending_limit=pending_limit
        self.blocks=OrderedDict();self.pending=deque();self.epoch=None
        self.last_sequence=None;self.dropped=0;self.missing_requests=0

    def reset(self, epoch):
        self.epoch=epoch;self.pending.clear();self.last_sequence=None
        # Verified content is reusable across scene/session generations.

    def add(self, key, data):
        data=bytes(data)
        if identity(data) != key:
            raise ValueError('Resource content does not match identity')
        if key in self.blocks:
            self.blocks.move_to_end(key);return
        # Never evict dependencies of a waiting state. Drop oldest waiting
        # presentation first when memory is exhausted, not a required tile.
        while len(self.blocks) >= self.capacity:
            pinned={k for state in self.pending for k in state.resources}
            victim=next((k for k in self.blocks if k not in pinned),None)
            if victim is not None:
                del self.blocks[victim];break
            self.pending.popleft();self.dropped+=1
        self.blocks[key]=data

    def submit(self, state):
        if state.epoch != self.epoch:
            raise ValueError('State from a different stream epoch')
        if self.last_sequence is not None:
            delta=(state.sequence-self.last_sequence)&0xffffffff
            if not 0 < delta < 0x80000000:
                raise ValueError('Duplicate or stale state')
        self.last_sequence=state.sequence
        if len(self.pending) == self.pending_limit:
            self.pending.popleft();self.dropped+=1
        self.pending.append(state)

    def missing(self):
        # Ordered and unique so one missing tile is requested once per batch.
        keys=dict.fromkeys(k for state in self.pending for k in state.resources
                           if k not in self.blocks)
        return tuple(keys)

    def ready(self):
        result=[]
        while self.pending:
            state=self.pending[0]
            if any(k not in self.blocks for k in state.resources):
                break
            self.pending.popleft()
            gfx=state.hot+b''.join(self.blocks[k] for k in state.resources)
            result.append((state,gfx))
        return result
