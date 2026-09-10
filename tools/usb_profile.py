"""Read-only timing wrapper. No change to vendor USB transport or read sizes."""
import threading
import time

class ReadProfile:
    def __init__(self, device):
        self.device=device
        self.lock=threading.Lock()
        self.calls=self.bytes=self.failures=0
        self.seconds=0.0
        self.sizes={}
    def __getattr__(self,name):
        return getattr(self.device,name)
    def read(self,endpoint,*args,**kwargs):
        start=time.perf_counter()
        try:
            data=self.device.read(endpoint,*args,**kwargs)
        except Exception:
            if endpoint==0x82:
                with self.lock:self.failures+=1
            raise
        if endpoint==0x82:
            elapsed=time.perf_counter()-start
            with self.lock:
                self.calls+=1;self.bytes+=len(data);self.seconds+=elapsed
                self.sizes[len(data)]=self.sizes.get(len(data),0)+1
        return data
    def snapshot(self):
        with self.lock:
            return dict(calls=self.calls,bytes=self.bytes,read_seconds=self.seconds,
                        failures=self.failures,sizes=dict(self.sizes))

def difference(before,after,elapsed):
    result={k:after[k]-before[k] for k in ('calls','bytes','read_seconds','failures')}
    result['sizes']={str(k):v-before['sizes'].get(k,0) for k,v in after['sizes'].items()
                     if v-before['sizes'].get(k,0)}
    result['bytes_s']=round(result['bytes']/elapsed,1)
    result['mean_successful_read_ms']=round(1000*result['read_seconds']/result['calls'],3) if result['calls'] else None
    result['scope']='Host USB reads including waiting; not Pico wire timestamps. Failures include timeouts.'
    return result
