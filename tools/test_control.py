"""Instruction-level PIO control checks; never opens a USB device."""
import random, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Machine:
 """The control state machine of the unified Pico firmware: autopull, shift right, 32-bit threshold."""
 def __init__(self, words):
  source=(ROOT/'firmware/unified/pico.c').read_text()
  self.code=[int(x,16) for x in re.search(r'control_code\[\]=\{([^}]+)',source)[1].split(',')]
  self.pc=0;self.x=0;self.y=0;self.osr=0;self.count=32;self.tx=list(words);self.direction=0;self.pin=0;self.stalled=0
 def step(self, clock):
  w=self.code[self.pc];op=w>>13;arg=w&31;dest=(w>>5)&7;next_pc=self.pc+1
  if op==7:
   if dest==1:self.x=arg
   elif dest==2:self.y=arg
   elif dest==4:self.direction=arg
   else:raise AssertionError('Unexpected SET destination')
  elif op==1:
   assert (w&0x7f)==0
   if clock!=bool(w&0x80):next_pc=self.pc
  elif op==0:
   if dest==0:take=True
   elif dest==6:take=bool(clock)
   elif dest==4:take=self.y!=0;self.y=(self.y-1)&0xffffffff
   elif dest==2:take=self.x!=0;self.x=(self.x-1)&0xffffffff
   else:raise AssertionError('Unexpected JMP condition')
   if take:next_pc=arg
  elif op==3:
   bits=arg or 32
   if self.count>=32:
    # empty output register: refilled from the FIFO first, or the instruction waits for data
    if not self.tx:self.stalled+=1;return
    self.osr=self.tx.pop(0);self.count=0
   value=self.osr&((1<<bits)-1);self.osr>>=bits;self.count+=bits
   if dest==0:assert bits==1;self.pin=value
   elif dest==1:self.x=value
   elif dest==3:pass
   else:raise AssertionError('Unexpected OUT destination')
  else:raise AssertionError('Unexpected opcode')
  self.pc=next_pc
 def run(self,clock,count):
  values=[]
  for _ in range(count):self.step(clock);values.append((self.direction,self.pin))
  return values

def slot_words(count,resync,payload):
 """Word 0 as the firmware builds it, then the verdict words."""
 return [(count-1)|(0x20000 if resync else 0)]+list(payload)

class Tests(unittest.TestCase):
 def test_program_fits_and_jumps_stay_inside(self):
  m=Machine([])
  self.assertLessEqual(len(m.code),32)
  for w in m.code:
   if w>>13==0:self.assertLess(w&31,len(m.code))
 def test_normal_clock_never_drives_data(self):
  m=Machine(slot_words(448,True,[0]*14))
  for _ in range(100):
   self.assertFalse(any(d for d,p in m.run(0,10)+m.run(1,10)))
 def test_extended_slot_delivers_every_bit_in_order_and_releases(self):
  rng=random.Random(5)
  for resync in (False,True):
   payload=[rng.getrandbits(32) for _ in range(14)]
   m=Machine(slot_words(448,resync,payload));m.run(0,10);m.run(1,200)
   self.assertEqual((m.direction,m.pin),(1,0))            # present
   m.run(0,30);m.run(1,30)
   self.assertEqual((m.direction,m.pin),(1,int(resync)))  # resync request
   got=[]
   for _ in range(448):
    m.run(0,3);m.run(1,6);self.assertEqual(m.direction,1);got.append(m.pin)
   want=[(payload[i>>5]>>(i&31))&1 for i in range(448)]
   self.assertEqual(got,want);self.assertEqual(m.stalled,0);self.assertEqual(m.tx,[])
   m.run(0,3);self.assertEqual(m.direction,0)
   self.assertFalse(any(d for d,p in m.run(1,50)+m.run(0,50)+m.run(1,1000)))
 def test_minimum_low_time_of_the_resident_is_enough(self):
  """The resident holds SC low for two register writes: two PIO cycles are enough to present the next bit."""
  payload=[0xa5a5a5a5]*14;m=Machine(slot_words(448,False,payload));m.run(0,10);m.run(1,200);m.run(0,30);m.run(1,30)
  got=[]
  for _ in range(448):m.run(0,2);m.run(1,3);got.append(m.pin)
  self.assertEqual(got,[(payload[i>>5]>>(i&31))&1 for i in range(448)])
 def test_resident_before_0_14_gets_two_bits_and_an_early_release(self):
  for resync in (False,True):
   m=Machine(slot_words(1,resync,[0xffffffff]*14));m.run(0,10);m.run(1,200)
   self.assertEqual((m.direction,m.pin),(1,0))
   m.run(0,30);m.run(1,30)
   self.assertEqual((m.direction,m.pin),(1,int(resync)))
   m.run(0,30)                      # old resident: SC low, short wait
   m.run(1,5);m.run(0,5)            # first of its fourteen flush pulses
   self.assertEqual(m.direction,0)
   for _ in range(13):self.assertFalse(any(d for d,p in m.run(1,5)+m.run(0,5)))

if __name__=='__main__':unittest.main()
