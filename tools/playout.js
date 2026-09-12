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
    // Late transport must not turn the buffer into seconds of old playback.
    if(this.base+this.clock<now-100) {
      this.dropped+=this.queue.length;this.queue=[];
      this.base=now+this.delay-this.clock;this.resets++;
    }
    this.queue.push({sequence,source,pixels,due:this.base+this.clock});
    if(this.queue.length>32){this.queue.shift();this.dropped++;}
    return true;
  }
  take(now) {
    let frame=null;
    while(this.queue.length && this.queue[0].due<=now) {
      if(frame)this.dropped++;
      frame=this.queue.shift();
    }
    if(frame)this.lastShown=frame.sequence;
    return frame;
  }
}
if(typeof module!=='undefined')module.exports={Playout};
