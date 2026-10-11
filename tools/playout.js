/* Source-clock playout. Repeated display refreshes are never new frames. */
class Playout {
  constructor(delay=200) {
    this.delay=delay;this.queue=[];this.lastSource=null;this.lastArrival=null;
    this.clock=0;this.base=null;this.lastShown=null;this.dropped=0;this.resets=0;
  }
  push(sequence,source,pixels,now) {
    source>>>=0;sequence>>>=0;
    if(this.lastSource!==null) {
      const delta=(source-this.lastSource)>>>0;
      if(delta===0)return false;
      // A pause/reset or a suspended browser starts a fresh bounded buffer.
      if(delta>120 || now-this.lastArrival>1000) {
        this.queue=[];this.base=null;this.clock=0;this.resets++;
      } else this.clock+=delta*(280896/16777216)*1000;
    }
    this.lastSource=source;this.lastArrival=now;
    if(this.base===null)this.base=now+this.delay-this.clock;
    // Frames released together after a scene load are late by design: they are played in order, faster than real
    // time (see take), instead of being thrown away. Only a buffer seconds behind starts over.
    if(this.base+this.clock<now-3000) {
      this.dropped+=this.queue.length;this.queue=[];
      this.base=now+this.delay-this.clock;this.resets++;
    }
    this.queue.push({sequence,source,pixels,due:this.base+this.clock});
    if(this.queue.length>96){this.queue.shift();this.dropped++;}
    return true;
  }
  take(now) {
    let due=0;
    while(due<this.queue.length && this.queue[due].due<=now)due++;
    if(!due)return null;
    // Up to three late frames are collapsed into the newest (jitter); a longer backlog (a fade replayed after a
    // load) is shown in order but about 20% faster per late frame until it is gone, so latency returns to normal.
    const pop=due<=3?due:1+Math.ceil(due/6);
    let frame=null;
    for(let i=0;i<pop;i++) {
      if(frame)this.dropped++;
      frame=this.queue.shift();
    }
    this.lastShown=frame.sequence;
    return frame;
  }
}
if(typeof module!=='undefined')module.exports={Playout};
