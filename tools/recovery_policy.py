"""Request recovery only for an unresolved fault, never for startup latency."""
class RecoveryPolicy:
 def __init__(self):self.faults=0;self.last_request=None;self.needed=False
 def update(self,now,faults,valid,pending):
  if valid:
   self.faults=faults;self.needed=False
   return False
  if faults>self.faults:self.needed=True
  self.faults=faults
  if self.needed and not pending and (self.last_request is None or now-self.last_request>=4):
   self.last_request=now;return True
  return False
