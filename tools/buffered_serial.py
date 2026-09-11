"""Bounded USB read pump: rendering cannot stall device draining."""
import queue,threading,time
class BufferedSerial:
 def __init__(self,serial):
  self.serial=serial;self.queue=queue.Queue(128);self.stop=threading.Event();self.error=None;self.peak_lag_ms=0
  self.worker=threading.Thread(target=self.pump,daemon=True);self.worker.start()
 def pump(self):
  try:
   while not self.stop.is_set():
    data=self.serial.read()
    if data:self.queue.put_nowait((time.monotonic(),data))
  except queue.Full:self.error=RuntimeError('Coda USB PC piena: conserva il rapporto');self.stop.set()
  except Exception as exc:self.error=exc;self.stop.set()
 def read(self):
  if self.error:raise self.error
  try:
   when,data=self.queue.get(timeout=.1);self.peak_lag_ms=max(self.peak_lag_ms,(time.monotonic()-when)*1000);return data
  except queue.Empty:return b''
 def write(self,data):return self.serial.write(data)
 def close(self):
  self.stop.set();self.worker.join(2)
  self.serial.close()
  if self.worker.is_alive():raise RuntimeError('Lettore USB non terminato')
