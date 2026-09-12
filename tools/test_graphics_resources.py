import unittest
from graphics_resources import Resources,State,identity

class Tests(unittest.TestCase):
    def test_late_resource_is_not_replaced_by_a_newer_version(self):
        a=bytes(256);b=b'x'*256;c=b'y'*256
        ka,kb,kc=map(identity,(a,b,c));r=Resources();r.reset(9);r.add(ka,a)
        first=State(9,1,100,bytes(2304),(kb,)+(ka,)*383)
        second=State(9,2,102,bytes(2304),(kc,)+(ka,)*383)
        r.submit(first);r.submit(second);r.add(kc,c)
        self.assertEqual(r.ready(),[])
        self.assertEqual(r.missing(),(kb,))
        r.add(kb,b);ready=r.ready()
        self.assertEqual([s.sequence for s,g in ready],[1,2])
        self.assertEqual(ready[0][1][2304:2560],b)
        self.assertEqual(ready[1][1][2304:2560],c)

    def test_corruption_epoch_and_reordering_rejected(self):
        r=Resources();r.reset(1);key=identity(bytes(256))
        with self.assertRaises(ValueError):r.add(key,b'x'*256)
        state=State(1,0xffffffff,1,bytes(2304),(key,)*384)
        r.submit(state)
        with self.assertRaises(ValueError):r.submit(state)
        r.submit(State(1,0,2,bytes(2304),(key,)*384))
        r.reset(2)
        with self.assertRaises(ValueError):r.submit(state)
        self.assertEqual(r.ready(),[])

    def test_waiting_queue_bounded(self):
        r=Resources(pending_limit=2);r.reset(1);key=identity(bytes(256))
        for i in range(10):r.submit(State(1,i,i*2,bytes(2304),(key,)*384))
        self.assertEqual(len(r.pending),2);self.assertEqual(r.dropped,8)
        r.add(key,bytes(256))
        self.assertEqual([s.sequence for s,g in r.ready()],[8,9])

if __name__=='__main__':unittest.main()
