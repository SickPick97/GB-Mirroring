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
console.log('OK: 30 Hz jittered source, distinct frames, wrap and pause recovery');
