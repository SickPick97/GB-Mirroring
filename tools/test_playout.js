const assert=require('node:assert/strict');
const {Playout}=require('./playout.js');
const period=280896/16777216*1000;
const p=new Playout(200);
let shown=0;
// 30 source states/s with deterministic USB jitter and a 60 Hz display.
for(let tick=0;tick<240;tick++) {
  if(tick%2===0)p.push(tick/2,tick,new Uint8Array(0),tick*period+(tick%6));
  if(p.take(tick*period))shown++;
}
assert(shown>=113 && shown<=115);
assert.equal(p.dropped,0);
assert.equal(p.take(239*period),null); // no fabricated repeated frames
const wrap=new Playout(200);
wrap.push(1,0xfffffffe,[],0);wrap.push(2,0,[],34);
assert.equal(wrap.resets,0);assert.equal(wrap.push(2,0,[],35),false);
assert.equal(wrap.take(200).sequence,1);
assert.equal(wrap.take(234).sequence,2);
wrap.push(3,500,[],3000);assert.equal(wrap.resets,1);
assert.equal(wrap.take(3100),null);assert.equal(wrap.take(3200).sequence,3);
// A burst of late, distinct frames (a move animation released after a wait) is shown completely and in order.
const burst=new Playout(200);
const picture=v=>{const b=new ArrayBuffer(16);new Uint32Array(b).fill(v);return b};
for(let i=0;i<12;i++)burst.push(i,i,picture(i),1000+i*0.1);
const seen=[];
for(let t=1000;t<1800;t+=period){const f=burst.take(t+400);if(f)seen.push(f.sequence)}
assert.deepEqual(seen,[0,1,2,3,4,5,6,7,8,9,10,11]);assert.equal(burst.dropped,0);
// Behind, with identical frames in the queue: those are skipped, nothing distinct is lost.
const still=new Playout(200);
for(let i=0;i<10;i++)still.push(i,i,picture(i<3?i:(i<8?3:i)),1000+i*0.1);
const kept=[];
for(let t=1000;t<1800;t+=period){const f=still.take(t+400);if(f)kept.push(new Uint32Array(f.pixels)[0])}
assert.deepEqual(kept,[0,1,2,3,8,9]);assert.equal(still.dropped,0);assert.equal(still.skipped,4);
console.log('OK: 30 Hz jittered source, distinct frames, wrap and pause recovery');
