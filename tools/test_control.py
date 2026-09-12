"""Instruction-level PIO control checks; never opens a USB device."""
import re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Machine:
 def __init__(self, command):
  source=(ROOT/'firmware/unified/pico.c').read_text()
  self.code=[int(x,16) for x in re.search(r'control_code\[\]=\{([^}]+)',source)[1].split(',')]
  self.pc=0;self.x=0;self.y=0;self.osr=0;self.tx=[command];self.direction=0;self.pin=0
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
   else:raise AssertionError('Unexpected JMP condition')
   if take:next_pc=arg
  elif op==4:
   assert w==0x8080
   self.osr=self.tx.pop(0) if self.tx else self.x
  elif op==3:
   assert dest==0 and arg==1
   self.pin=self.osr&1;self.osr>>=1
  else:raise AssertionError('Unexpected opcode')
  self.pc=next_pc
 def run(self,clock,count):
  values=[]
  for _ in range(count):self.step(clock);values.append((self.direction,self.pin))
  return values

class Tests(unittest.TestCase):
 def test_normal_clock_never_drives_data(self):
  m=Machine(2)
  for _ in range(100):
   self.assertFalse(any(d for d,p in m.run(0,10)+m.run(1,10)))
 def test_control_word_and_release(self):
  for command in (0,2):
   m=Machine(command);m.run(0,10);m.run(1,200)
   self.assertEqual((m.direction,m.pin),(1,0))
   m.run(0,30);m.run(1,30)
   self.assertEqual((m.direction,m.pin),(1,command>>1))
   m.run(0,30);self.assertEqual(m.direction,0)
   self.assertFalse(any(d for d,p in m.run(1,1000)))

if __name__=='__main__':unittest.main()
