"""Windows CDC via system API; no pyserial dependency."""
import ctypes as c
from ctypes import wintypes as w
class Timeouts(c.Structure):
 _fields_=[(x,w.DWORD) for x in ('interval','rm','rc','wm','wc')]
class Serial:
 def __init__(self,port,read_timeout=50):
  k=self.k=c.WinDLL('kernel32',use_last_error=True)
  k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE];k.CreateFileW.restype=w.HANDLE
  k.ReadFile.argtypes=[w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p];k.ReadFile.restype=w.BOOL
  k.WriteFile.argtypes=k.ReadFile.argtypes;k.WriteFile.restype=w.BOOL
  k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
  k.SetCommTimeouts.argtypes=[w.HANDLE,c.POINTER(Timeouts)];k.SetCommTimeouts.restype=w.BOOL
  k.EscapeCommFunction.argtypes=[w.HANDLE,w.DWORD];k.EscapeCommFunction.restype=w.BOOL
  self.handle=k.CreateFileW(chr(92)*2+'.'+chr(92)+port,0xc0000000,0,None,3,0,None)
  if self.handle==c.c_void_p(-1).value:self.handle=None;raise c.WinError(c.get_last_error())
  try:
   self.check(k.SetCommTimeouts(self.handle,c.byref(Timeouts(min(10,read_timeout),0,read_timeout,0,2000))))
   self.check(k.EscapeCommFunction(self.handle,5))
  except Exception:self.close();raise
 def check(self,result):
  if not result:raise c.WinError(c.get_last_error())
 def read(self):
  buf=c.create_string_buffer(8192);n=w.DWORD();self.check(self.k.ReadFile(self.handle,buf,len(buf),c.byref(n),None));return buf.raw[:n.value]
 def write(self,data):
  buf=c.create_string_buffer(data);n=w.DWORD();self.check(self.k.WriteFile(self.handle,buf,len(data),c.byref(n),None))
  if n.value!=len(data):raise OSError('Partial serial write')
 def close(self):
  if self.handle is not None:self.k.CloseHandle(self.handle);self.handle=None
