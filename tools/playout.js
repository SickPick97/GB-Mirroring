/* Source-clock playout. Repeated display refreshes are never new frames. */
class Playout {
  constructor(delay=200) {
    this.delay=delay;this.queue=[];this.lastSource=null;this.lastArrival=null;
    this.clock=0;this.base=null;this.lastShown=null;this.dropped=0;this.resets=0;this.skipped=0;this.lastPixels=null;
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
    const same=Playout.equal(pixels,this.lastPixels);this.lastPixels=pixels;
    this.queue.push({sequence,source,pixels,due:this.base+this.clock,same});
    if(this.queue.length>96){this.queue.shift();this.dropped++;}
    return true;
  }
  take(now) {
    let due=0;
    while(due<this.queue.length && this.queue[due].due<=now)due++;
    if(!due)return null;
    // Frames that arrive together (a wait for missing blocks, then all at once) are shown one per refresh, in order:
    // 0.13.2-0.15.0 dropped up to two out of three of them and battle moves lost most of their frames. The delay is
    // made up by skipping frames identical to the one before them (text waiting, a still screen), which costs nothing
    // to see. Only more than a fifth of a second of distinct frames behind drops one of them per refresh.
    let frame=this.queue.shift();due--;
    while(due>0 && this.queue[0].same){frame=this.queue.shift();due--;this.skipped++;}
    if(due>12){frame=this.queue.shift();this.dropped++;}
    this.lastShown=frame.sequence;
    return frame;
  }
  static equal(a,b) {
    if(!(a instanceof ArrayBuffer) || !(b instanceof ArrayBuffer) || a.byteLength!==b.byteLength || !a.byteLength || a.byteLength&3)return false;
    const x=new Uint32Array(a),y=new Uint32Array(b);
    for(let i=0;i<x.length;i++)if(x[i]!==y[i])return false;
    return true;
  }
}
if(typeof module!=='undefined')module.exports={Playout};
