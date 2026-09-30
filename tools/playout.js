/* Source-clock playout. Repeated display refreshes are never new frames. */
class Playout {
  constructor(delay=200) {
    this.delay=delay;this.queue=[];this.lastSource=null;this.lastArrival=null;
    this.clock=0;this.base=null;this.lastShown=null;this.dropped=0;this.resets=0;this.skew=0;this.caughtUp=0;
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
    if(this.base===null){this.base=now+this.delay-this.clock;this.skew=0;}
    // Late transport must not turn the buffer into seconds of old playback.
    if(this.base+this.clock-this.skew<now-100) {
      this.dropped+=this.queue.length;this.queue=[];
      this.base=now+this.delay-this.clock;this.skew=0;this.resets++;
    }
    this.queue.push({sequence,source,pixels,due:this.base+this.clock});
    if(this.queue.length>64){this.queue.shift();this.dropped++;}
    return true;
  }
  take(now) {
    // After a scene load the replayed fade-in leaves the buffer behind the live stream: play half a frame faster per
    // display frame until only the normal delay is queued again.
    const last=this.queue.length?this.queue[this.queue.length-1].due-this.skew:0;
    if(this.queue.length && last-now>this.delay+60){this.skew+=8;this.caughtUp++;}
    let frame=null;
    while(this.queue.length && this.queue[0].due-this.skew<=now) {
      if(frame)this.dropped++;
      frame=this.queue.shift();
    }
    if(frame)this.lastShown=frame.sequence;
    return frame;
  }
}
if(typeof module!=='undefined')module.exports={Playout};
