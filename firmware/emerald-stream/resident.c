#include <stdint.h>
#define U8(a) (*(volatile uint8_t*)(a))
#define U16(a) (*(volatile uint16_t*)(a))
#define U32(a) (*(volatile uint32_t*)(a))
extern uint32_t original_irq;
extern void vb_thunk(void);
volatile uint32_t orig_vblank;
extern unsigned scan_next(unsigned,const void*,const void*,uint32_t*);
extern void sb_sig(const volatile void*,uint16_t*);
extern uint8_t fast_begin[],fast_end[],hash_begin[],hash_end[];
extern unsigned pending_count(const uint32_t*,uint32_t*);
extern unsigned words_equal(const volatile uint32_t*,const volatile uint32_t*,unsigned);
extern void copy16(uint16_t*,const volatile uint16_t*,unsigned);
extern void patch_apply(uint16_t*,const uint16_t*,unsigned);
extern uint32_t crc32_arm(const uint16_t*,unsigned);
void tick(void);
#ifndef DEADLINE
#define DEADLINE 24
#endif
/* Stream 0.13: one tick packet per VBlank (registers, palette, OAM, ROM replays and a small slice of VRAM),
   plus bulk packets sent while the game waits for the next VBlank. Both run with the game's interrupts enabled:
   the resident never holds off an HBlank, VCount, timer or VBlank interrupt of the game. */
#define FIELDS 6
#define PAY_MAX 224
#define FEEDBACK_EVERY 30
/* Bulk work while the game is idle stops at this scanline, well before VBlank (160). */
#ifndef IDLE_END
#define IDLE_END 156
#endif
/* Timer 1 (unused by the game during play; its slot in the game's interrupt table is a dummy) checks for idle
   time every ten scanlines: 64-cycle prescaler, 193 counts. */
#define TIMER_STEP 193
#ifndef LONG_BUSY
#define LONG_BUSY 30
#endif
#ifndef HEAVY_SLACK
#define HEAVY_SLACK 40
#endif
static uint32_t hashes[393];
uint32_t dirty_mask[13];
static uint32_t strong_mask[13],other_mask[13];
/* Copies observed before a VBlank are only merged after it, once the game has actually performed them. */
static uint32_t nx_dirty[13],nx_other[13];
#define RQ 6
static uint32_t rq[RQ][3],rp[4][3];static unsigned rq_n,rp_n;
static unsigned audit_cursor,feedback,vblank_seen,bulk_cursor=9,cadence=1,skip,held2;
/* Codecs write straight into the packet; the slack lets a 128-word body be built past the limit and dropped. */
static uint16_t packet[12+PAY_MAX+127];
static uint32_t regblock[64];
static uint32_t sequence,last_vblank,valid,enabled,held;
static uint32_t since_key,since_feedback,tick_frame,key;
/* 64 remembered block contents, keyed by the folded hash (h0 ^ h1*C); the PC keeps the content. */
static uint32_t dict_fold[64],known[2];
static uint16_t previous_hot[560];
/* Screen blocks 28..30 (blocks 233..256, eight per layer): signatures of 16 column pairs and 16 row pairs
   of the last content the PC is known to hold. A layer is patched as one unit or sent block by block. */
static uint16_t sb_sigs[3][32];
static uint32_t sb_known,sb_dim;  /* sb_dim: 2 bits per layer, 0 both signature sets valid, 1 columns only, 2 rows only (send in progress) */
static inline unsigned pc16(unsigned v){unsigned n=0;while(v){v&=v-1;n++;}return n;}
static uint32_t hot_known;
static uint32_t peak_lines,last_words,optimized=2;
#ifdef SOFT
volatile uint32_t ticks_sent,busy_skips,last_busy_pc;
#define DEBUG_COUNT(x) x
#else
#define DEBUG_COUNT(x)
#endif
volatile uint32_t visits,entry_line,scan_limit=228,scan_stop=393,irq_lr,in_work,tick_owed;
static unsigned busy_run,starved,skipped,mode,observed,idle_ran,idle_words,idle_first;
#ifdef SOFT
volatile uint32_t dbg_words,dbg_lines,dbg_fill,dbg_end;
#endif
/* Scanlines needed to send `pay` words (CRC and bit clocking), measured at about six words per scanline. */
static inline unsigned send_lines(unsigned pay){return (pay*43)>>8;}
static inline unsigned elapsed_lines(unsigned line){unsigned d=line+228-entry_line;return d>=228?d-228:d;}
#define BIT(b) (1u<<((b)&31))
/* After a scene change every block is unverified: counted as pending so the PC holds its image until checked. */
__attribute__((section(".scheduler"))) static void mark_all(void){
 for(unsigned i=0;i<13;i++){dirty_mask[i]=~0u;strong_mask[i]=~0u;other_mask[i]=~0u;}
 dirty_mask[12]=strong_mask[12]=other_mask[12]=511;
}
/* Italian BPEI pointers are checked by the loader. Read only pending copy metadata. */
__attribute__((section(".scheduler"))) static void mark_range(uint32_t address,unsigned size,unsigned other){
 if(address<0x06000000 || address>=0x06018000 || !size)return;
 unsigned end=address+size;if(end<address || end>0x06018000)end=0x06018000;
 unsigned first=9+((address-0x06000000)>>8),last=9+((end-1-0x06000000)>>8);
 for(unsigned b=first;b<=last;b++){nx_dirty[b>>5]|=BIT(b);if(other)nx_other[b>>5]|=BIT(b);}
}
/* A pending copy whose source is the ROM can be replayed by the PC from its own cartridge
   image once the GBA has confirmed that VRAM really holds those ROM bytes. */
__attribute__((section(".scheduler"))) static void request(uint32_t src,uint32_t dest,unsigned size){
 unsigned rom=size && src>=0x08000000 && src<0x09000000 && !((src|dest|size)&3) && size<=0x2000 && dest>=0x06000000 && dest+size<=0x06018000 && rq_n<RQ;
 if(rom){rq[rq_n][0]=src;rq[rq_n][1]=dest;rq[rq_n][2]=size;rq_n++;}
 mark_range(dest,size,!rom);
}
/* Reads the game's copy queues once per frame: when the game starts waiting for VBlank (from the idle timer), or
   else from inside its VBlank callback (vb_thunk, known scenes only). Never before the game's interrupt handler:
   a delay there starved the VBlank interrupt during the battle transition and froze the game. */
__attribute__((section(".scheduler"))) void observe(void){
 if(!enabled || observed)return;
 observed=1;
 if(!U8(0x03000810)){
  unsigned index=U8(0x03000811);
  for(unsigned n=0;n<128;n++,index=(index+1)&127){
   uint32_t a=0x03000010+index*16;unsigned size=U16(a+8);if(!size)break;
   request(U32(a),U32(a+4),size);
  }
 }
 /* Tileset animation transfers: 12-byte {src,dest,size} entries, pending count in IWRAM. */
 {unsigned count=U8(0x03000f34);if(count>20)count=20;
  for(unsigned i=0;i<count;i++){uint32_t a=0x02037624+i*12;request(U32(a),U32(a+4),U16(a+8));}}
 if(U8(0x02021834)){
  unsigned count=U8(0x02021835);if(count>64)count=64;
  for(unsigned i=0;i<count;i++){uint32_t a=0x02021838+i*12;request(U32(a),U32(a+4),U16(a+8));}
 }
}
__attribute__((section(".scheduler"))) static uint16_t crc16(const uint16_t*d,unsigned n){
 static const uint16_t t[16]={0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 uint16_t c=65535;for(unsigned i=0;i<n;i++){unsigned w=d[i];
 for(unsigned j=0;j<2;j++){c^=(w&255)<<8;w>>=8;c=(c<<4)^t[c>>12];c=(c<<4)^t[c>>12];}}
 return c;
}
__attribute__((section(".scheduler"))) static void emit(unsigned version,unsigned type,unsigned block,unsigned n){
 packet[0]=0xb47e;packet[1]=0x5647;packet[2]=version;packet[3]=type;packet[4]=sequence;packet[5]=sequence>>16;packet[6]=n;packet[7]=block;
 uint32_t c=crc32_arm(packet+12,n);packet[8]=c;packet[9]=c>>16;packet[10]=crc16(packet+2,8);packet[11]=0x5aa5;
 ((void(*)(const uint16_t*,unsigned))fast_begin)(packet,n+12);
}
__attribute__((noinline)) static unsigned compress(const volatile uint16_t *src,uint16_t*out){
 unsigned n=0,i=0;
 while(i<128){unsigned v=src[i],count=1;while(i+count<128 && src[i+count]==v)count++;
  if(n+2>=128)return 128;
  out[n++]=count;out[n++]=v;i+=count;
 }
 return n;
}
__attribute__((noinline)) static unsigned compress_patch(const volatile uint16_t*words,const uint16_t*previous,unsigned count,uint16_t*out){
 unsigned changes=0;
 for(unsigned i=0;i<count;i++)changes+=words[i]!=previous[i];
 if(changes+8>=128)return 128;
 unsigned n=8;for(unsigned i=0;i<8;i++)out[i]=0;
 for(unsigned i=0;i<count;i++)if(words[i]!=previous[i]){out[i>>4]|=1u<<(i&15);out[n++]=words[i];}
 return n;
}
/* Explicit half-duplex slot: GBA releases SD before holding SC high.
   Pico releases SD on the final falling edge before GBA drives it again. */
__attribute__((section(".scheduler"))) static void poll_control(void){
 U16(0x04000134)=0x8010;
 U16(0x04000134)=0x8011;
 for(volatile unsigned i=0;i<128;i++){}
 unsigned a=U16(0x04000134)&2;
 U16(0x04000134)=0x8010;
 for(volatile unsigned i=0;i<16;i++){}
 U16(0x04000134)=0x8011;
 for(volatile unsigned i=0;i<16;i++){}
 unsigned b=U16(0x04000134)&2;
 U16(0x04000134)=0x8010;
 for(volatile unsigned i=0;i<16;i++){}
 /* Finish a full 16-edge idle group before the next framed packet. */
 for(unsigned i=0;i<14;i++){U16(0x04000134)=0x8011;U16(0x04000134)=0x8010;}
 U16(0x04000134)=0x8030;
 feedback=!a;if(!a && b)valid=0;
}
/* The Pico only recognizes this exact 0.6/0.7 END layout; it opens the feedback slot after it. */
__attribute__((section(".scheduler"))) static void control_slot(uint32_t now){
 uint16_t*p=packet+12;
 p[0]=now;p[1]=now>>16;p[2]=0;p[3]=0;p[4]=now;p[5]=now>>16;p[6]=1;p[7]=last_words;p[8]=0;p[9]=peak_lines;
 p[10]=optimized|(feedback<<8)|16384;p[11]=visits;
 emit(0x600,2,0,12);
 /* Flush the final END bits from a possibly shifted 16-bit RX group. */
 packet[0]=0;((void(*)(const uint16_t*,unsigned))fast_begin)(packet,1);
 poll_control();
}
/* Confirm queued ROM copies against VRAM and clear the blocks they fully explain.
   Confirmed copies are emitted at the end of this tick's packet; their space is reserved. */
__attribute__((section(".scheduler"))) static unsigned confirm_requests(void){
 rp_n=0;
 /* Comparing and hashing are capped per tick: a scene load queues thousands of words. */
 unsigned cap=1024;
 for(unsigned i=0;i<rq_n;i++){
  uint32_t src=rq[i][0],dest=rq[i][1];unsigned size=rq[i][2];
  unsigned first=9+((dest-0x06000000)>>8),last=9+((dest+size-1-0x06000000)>>8),w=size>>2,fits=w<=cap;
  if(fits)cap-=w;
  /* Screen blocks 28..30 (233..256) use signature patches against the last sent copy: keep them literal. */
  if(rp_n>=4 || (first<=256 && last>=233) || !fits || !words_equal((const volatile uint32_t*)dest,(const volatile uint32_t*)src,size)){
   for(unsigned b=first;b<=last;b++)other_mask[b>>5]|=BIT(b);
   continue;
  }
  rp[rp_n][0]=src;rp[rp_n][1]=dest;rp[rp_n][2]=size;rp_n++;
  for(unsigned b=first;b<=last;b++){
   if(other_mask[b>>5]&BIT(b))continue;
   dirty_mask[b>>5]&=~BIT(b);strong_mask[b>>5]&=~BIT(b);
   uint32_t base=0x06000000+(b-9)*256;
   if(dest<=base && dest+size>=base+256){uint32_t h[2];((void(*)(const void*,uint32_t*))hash_begin)((const void*)base,h);hashes[b]=h[0]^(h[1]*0x9e3779b1u);}
  }
 }
 rq_n=0;
 return rp_n*7;
}
__attribute__((section(".scheduler"))) static unsigned emit_replays(unsigned pay,unsigned*records){
 for(unsigned i=0;i<rp_n;i++){
  uint32_t src=rp[i][0],dest=rp[i][1];unsigned size=rp[i][2];
  uint16_t*out=packet+12+pay;
  out[0]=9+((dest-0x06000000)>>8);out[1]=(10<<8)|5;out[2]=src;out[3]=src>>16;out[4]=dest;out[5]=dest>>16;out[6]=size;
  pay+=7;(*records)++;
 }
 return pay;
}
/* Known scenes get the thunk in front of the game's VBlank callback (fallback when the game had no idle time
   before VBlank); anything else is left untouched. Returns the game's real callback. */
__attribute__((section(".scheduler"))) static unsigned hooked_callback(void){
 uint32_t cb=U32(0x030022cc);
 if(cb==(uint32_t)vb_thunk)return orig_vblank;
 if(cb==0x080863a5 || cb==0x080bb399 || cb==0x081afcd5){orig_vblank=cb;U32(0x030022cc)=(uint32_t)vb_thunk;}
 return cb;
}
__attribute__((section(".scheduler"))) static void timer_off(void){
 U16(0x04000106)=0;U16(0x04000200)&=~0x10;U16(0x04000202)=0x10;
}
__attribute__((section(".scheduler"))) static void timer_arm(void){
 U16(0x04000106)=0;U16(0x04000104)=65536-TIMER_STEP;U16(0x04000202)=0x10;U16(0x04000106)=0xc1;U16(0x04000200)|=0x10;
}
/* Sends changed VRAM blocks into the packet from `pay` on, until `limit` words or `deadline` scanlines after
   entry_line. Stage 0 starts with registers, palette and OAM (never held back by the time budget); stage 1 and 2
   walk the bulk blocks round robin from bulk_cursor. `strict` (idle time) also reserves the cost of the next block
   (up to 22 scanlines), so the packet is finished by the deadline instead of starting there. */
#define ITEM_LINES 22
__attribute__((section(".scheduler"))) static unsigned fill(unsigned pay,unsigned limit,unsigned deadline,unsigned stage,unsigned strict,unsigned gate_hot,unsigned*records,unsigned*bulk){
 unsigned cursor=stage?bulk_cursor:0,margin=strict?ITEM_LINES:0;
 for(;;){
  unsigned line=U16(0x04000006);
  unsigned budget=send_lines(pay),gated=stage!=0 || gate_hot;
  if(pay+3>limit || (gated && elapsed_lines(line)+budget+margin>=deadline))break;
  scan_limit=gated?(deadline>budget+margin?deadline-budget-margin:1):228;
  scan_stop=stage==0?9:(stage==2?bulk_cursor:393);
  uint32_t h[3];unsigned next=scan_next(cursor,regblock,hashes,h);
  if(next&0x80000000)break;
  unsigned block=next;
  if(stage==0 && block>=9){stage=1;cursor=bulk_cursor;continue;}
  if(block==393){
   if(stage==1 && bulk_cursor>9){stage=2;cursor=9;continue;}
   break;
  }
  if(stage==2 && block>=bulk_cursor)break;
  if(block>=233 && block<257 && (sb_known&(1u<<((block-233)>>3)))){
   unsigned k=(block-233)>>3,first=233+(k<<3);
   const volatile uint8_t*base=(const volatile uint8_t*)(0x06000000+(first-9)*256);
   uint16_t sig[32];sb_sig(base,sig);
   unsigned colmask=0,rowmask=0;
   for(unsigned i=0;i<16;i++){if(sig[i]!=sb_sigs[k][i])colmask|=1u<<i;if(sig[16+i]!=sb_sigs[k][16+i])rowmask|=1u<<i;}
   /* Every changed cell lies in a changed column pair and in a changed row pair, so either set covers
      all changes: send the smaller one. */
   {unsigned dim=(sb_dim>>(2*k))&3,cc=pc16(colmask),rc=pc16(rowmask);
    if(dim==1)rowmask=0;else if(dim==2)colmask=0;else if(cc && rc){if(cc<=rc)rowmask=0;else colmask=0;}}
   unsigned groups=pc16(colmask)+pc16(rowmask);
   /* Whatever does not fit in this packet is sent by the next ones; only the sent groups update the signatures. */
   unsigned fit=pay+7<=limit?(limit-pay-7)/64:0,partial=0;
   if(strict){unsigned used=elapsed_lines(U16(0x04000006))+send_lines(pay)+8,room=deadline>used?(deadline-used)*6/64:0;if(fit>room)fit=room;}
   if(!fit && groups){strong_mask[block>>5]|=BIT(block);break;}
   if(groups>fit){
    unsigned keep_c=0,keep_r=0,left=fit;
    for(unsigned i=0;i<16 && left;i++)if(colmask&(1u<<i)){keep_c|=1u<<i;left--;}
    for(unsigned i=0;i<16 && left;i++)if(rowmask&(1u<<i)){keep_r|=1u<<i;left--;}
    colmask=keep_c;rowmask=keep_r;groups=fit;partial=1;
   }
   unsigned un=5+groups*64;
   uint32_t fold=0,bf[8];
   for(unsigned i=0;i<8;i++){uint32_t hh[2];((void(*)(const void*,uint32_t*))hash_begin)((const void*)(base+i*256),hh);bf[i]=hh[0]^(hh[1]*0x9e3779b1u);fold^=bf[i];}
   uint16_t*urec=packet+12+pay,*ubody=urec+2;
   ubody[0]=partial;ubody[1]=colmask;ubody[2]=rowmask;ubody[3]=fold;ubody[4]=fold>>16;
   unsigned pos=5;
   for(unsigned g=0;g<16;g++)if(colmask&(1u<<g))for(unsigned r=0;r<32;r++){uint32_t w=*(const volatile uint32_t*)(base+r*64+g*4);ubody[pos++]=w;ubody[pos++]=w>>16;}
   for(unsigned q=0;q<16;q++)if(rowmask&(1u<<q)){copy16(ubody+pos,(const volatile uint16_t*)(base+q*128),64);pos+=64;}
   urec[0]=first;urec[1]=(12<<8)|un;
   pay+=un+2;(*records)++;(*bulk)++;
   if(partial){
    for(unsigned i=0;i<16;i++){if(colmask&(1u<<i))sb_sigs[k][i]=sig[i];if(rowmask&(1u<<i))sb_sigs[k][16+i]=sig[16+i];}
    sb_dim=(sb_dim&~(3u<<(2*k)))|((colmask?1u:2u)<<(2*k));
   }else{for(unsigned i=0;i<32;i++)sb_sigs[k][i]=sig[i];sb_dim&=~(3u<<(2*k));}
   if(partial){for(unsigned i=0;i<8;i++){unsigned b=first+i;strong_mask[b>>5]|=BIT(b);}break;}
   for(unsigned i=0;i<8;i++){unsigned b=first+i;hashes[b]=bf[i];dirty_mask[b>>5]&=~BIT(b);strong_mask[b>>5]&=~BIT(b);}
   cursor=first+8;if(stage)bulk_cursor=cursor>=393?9:cursor;
   continue;
  }
  const volatile uint32_t *src=(const volatile uint32_t*)h[2];
  unsigned hot=block==0?0:(block>=5 && block<9?block-4:5);
  uint32_t fold32=h[0]^(h[1]*0x9e3779b1u);
  unsigned slot=(fold32*2654435761u)>>26,type=1,n=128;
  uint16_t*rec=packet+12+pay,*body=rec+2;
  if((known[slot>>5]&BIT(slot)) && fold32==dict_fold[slot]){type=3;n=1;body[0]=slot;}
  if(type==1){
   if(hot<5 && (hot_known&(1u<<hot))){n=compress_patch((const volatile uint16_t*)src,(previous_hot+(hot?48+(hot-1)*128:0)),hot?128:48,body);if(n<128)type=5;}
   if(n==128){n=compress((const volatile uint16_t*)src,body);if(n<128)type=4;}
  }
  if(n>=128){type=1;n=128;}
  if(pay+2+n>limit){
   /* Known changed but no room: keep it pending and report it. */
   strong_mask[block>>5]|=BIT(block);
   break;
  }
  if(type==1)copy16(body,(const volatile uint16_t*)src,128);
  rec[0]=type==3?block:(slot<<9)|block;rec[1]=(type<<8)|n;
  pay+=n+2;(*records)++;if(block>=9)(*bulk)++;
  hashes[block]=fold32;dict_fold[slot]=fold32;known[slot>>5]|=BIT(slot);
  if(hot<5){
   uint16_t*previous=previous_hot+(hot?48+(hot-1)*128:0);unsigned count=hot?128u:48u;
   if(type==5)patch_apply(previous,body,count);
   else copy16(previous,(const volatile uint16_t*)src,count);
   hot_known|=1u<<hot;
  }
  dirty_mask[block>>5]&=~BIT(block);strong_mask[block>>5]&=~BIT(block);
  cursor=block+1;if(stage)bulk_cursor=cursor>=393?9:cursor;
 }
 /* A layer whose eight blocks are all clean holds exactly what the PC holds: learn its signatures. */
 for(unsigned k=0;k<3;k++)if(!(sb_known&(1u<<k))){
  unsigned first=233+(k<<3),clean=1;
  for(unsigned i=0;i<8;i++){unsigned b=first+i;if(dirty_mask[b>>5]&BIT(b))clean=0;}
  if(clean){sb_sig((const volatile void*)(0x06000000+(first-9)*256),sb_sigs[k]);sb_known|=1u<<k;}
 }
 return pay;
}
__attribute__((section(".scheduler"))) static unsigned fields(unsigned idle,unsigned pending,unsigned records,unsigned ie,unsigned callback){
 uint16_t*f=packet+12;
 f[0]=(idle?0:key)|((U16(0x040000ba)&0x8000)?2:0)|((skipped>7?7:skipped)<<4)|(mode<<11)|(feedback<<8)|(cadence<<9)|0x2000;
 f[1]=tick_frame;f[2]=tick_frame>>16;f[3]=pending|((ie&0x6f)<<9);f[4]=records|(((callback^(callback>>8)^(callback>>16))&255)<<8);
 f[5]=idle?(idle_words>65535?65535:idle_words):((peak_lines>255?255:peak_lines)|((last_words>255?255:last_words)<<8));
 return pending;
}
/* Tiles of every visible sprite are verified each frame: the game redraws some of them in place (health bars, text in
   boxes, battle sprites) without any copy request, and a rotating audit alone would show those changes in steps. */
__attribute__((section(".scheduler"))) static void mark_objects(void){
 static const uint8_t tiles[3][4]={{1,4,16,64},{2,4,8,32},{2,4,8,32}};
 const volatile uint16_t*oam=(const volatile uint16_t*)0x07000000;
 for(unsigned i=0;i<128;i++,oam+=4){
  unsigned a0=oam[0],a1=oam[1],a2=oam[2],shape=a0>>14;
  if((a0&0x300)==0x200 || shape==3)continue;
  unsigned n=tiles[shape][a1>>14];if(a0&0x2000)n*=2;
  unsigned first=265+((a2&1023)>>3),last=265+(((a2&1023)+n-1)>>3);if(last>392)last=392;
  for(unsigned b=first;b<=last;b++){dirty_mask[b>>5]|=BIT(b);other_mask[b>>5]|=BIT(b);}
 }
}
/* Entered from the timer 1 interrupt when the game waits for VBlank (interrupted inside its WaitForVBlank loop with
   the VBlank flag clear), in system mode with interrupts enabled. Reads the copy queues, then sends pending blocks
   and audits the rest of VRAM until IDLE_END. Runs only between ticks, so it never overlaps one. */
__attribute__((section(".scheduler"))) void idle(void){
 if(!enabled || !valid){timer_off();return;}
 unsigned line=U16(0x04000006);
 if(line>=IDLE_END){timer_off();return;}
 observe();
 if(!idle_ran)mark_objects();
 idle_ran=1;if(!idle_first)idle_first=line+1;
 unsigned audited=0,callback=vblank_seen,ie=U16(0x04000200);
 for(;;){
  /* Stop as soon as VBlank has come (the game wants to run its frame) or too little time is left for a block. */
  line=U16(0x04000006);
  if((U16(0x030022dc)&1) || line+ITEM_LINES+2>=IDLE_END)break;
  entry_line=line;
  unsigned pay=FIELDS,records=0,bulk=0;
  /* Registers (the tick's snapshot), palette and OAM only change at VBlank: those a heavy tick left pending go first. */
  pay=fill(pay,PAY_MAX,IDLE_END-line,0,1,1,&records,&bulk);
  if(records){
   unsigned pending=pending_count(dirty_mask,strong_mask);
   for(unsigned i=0;i<13;i++)other_mask[i]&=dirty_mask[i];
   fields(1,pending,records,ie,callback);
#ifdef SOFT
   {unsigned a=U16(0x04000006);
#endif
   emit(0x700,13,0,pay);
#ifdef SOFT
   unsigned b=U16(0x04000006);if(b<160 && b>=a){dbg_words+=pay+12;dbg_lines+=b-a;dbg_fill+=a-line;}else if(a>dbg_end)dbg_end=a;}
#endif
   idle_words+=pay+12;sequence++;
   continue;
  }
  /* Nothing known to be pending: verify more of VRAM, one full sweep per frame at most. */
  if(audited>=384 || U16(0x04000006)+ITEM_LINES+2>=IDLE_END)break;
  for(unsigned i=0;i<24;i++){unsigned b=9+audit_cursor;dirty_mask[b>>5]|=BIT(b);other_mask[b>>5]|=BIT(b);if(++audit_cursor==384)audit_cursor=0;}
  audited+=24;
 }
 timer_off();
 /* VBlank came while this was sending: the wrapper could not start the tick then, so run it now. */
 if(tick_owed){tick_owed=0;irq_lr=0x080008ca;tick();}
}
/* The game's scanline effect (gScanlineEffect at 0x02039b28 in the Italian BPEI: double buffer, destination register,
   DMA control, current buffer): an HBlank DMA copies one value per line into a video register (battle intro slide,
   waves). The table on screen is sent when it changes, in two halves of 80 lines, run-length coded when shorter;
   the PC applies the values line by line. DMA set up by other code (some battle transitions) is not known. */
static uint32_t raster_fold;
__attribute__((section(".scheduler"))) static unsigned raster(unsigned pay,unsigned limit,unsigned*records){
 unsigned cnt=U16(0x040000ba);
 if(!(cnt&0x8000) || ((cnt>>12)&3)!=2){raster_fold=0;return pay;}
 const volatile uint32_t*se=(const volatile uint32_t*)0x02039b28;
 uint32_t ctl=se[3],dest=se[2],src=se[(U8(0x02039b3c)^1)&1];
 if((ctl>>16)!=cnt || (ctl&0x0400ffffu)!=1 || dest<0x04000008 || dest>=0x04000060 || (dest&1) || src<0x02000002 || src>=0x02040000 || (src&1))return pay;
 const volatile uint16_t*base=(const volatile uint16_t*)(src-2);
 uint32_t h=dest;for(unsigned i=0;i<160;i++)h=(h^base[i])*0x9e3779b1u;
 if(!h)h=1;
 if(h==raster_fold)return pay;
 unsigned start=pay;
 for(unsigned part=0;part<2;part++){
  const volatile uint16_t*v=base+part*80;
  uint16_t*rec=packet+12+pay,*body=rec+2;unsigned n=1;
  for(unsigned i=0;i<80 && n<80;){unsigned c=1;while(i+c<80 && v[i+c]==v[i])c++;body[n++]=c;body[n++]=v[i];i+=c;}
  unsigned rle=n<80;
  if(!rle){n=81;for(unsigned i=0;i<80;i++)body[1+i]=v[i];}
  if(pay+2+n>limit)return start;
  body[0]=(dest-0x04000000)|(part<<10)|(rle<<11);
  rec[0]=0;rec[1]=(13<<8)|n;pay+=2+n;(*records)++;
 }
 raster_fold=h;return pay;
}
__attribute__((section(".scheduler"))) void tick(void){
 uint32_t now=U32(0x030022e0);if(now==last_vblank)return;last_vblank=now;visits++;
 /* The copies observed before this VBlank have been performed by the game's handler now. */
 for(unsigned i=0;i<13;i++){dirty_mask[i]|=nx_dirty[i];strong_mask[i]|=nx_dirty[i];other_mask[i]|=nx_other[i];nx_dirty[i]=nx_other[i]=0;}
 observed=0;
 unsigned callback=hooked_callback();
 unsigned pressed=(U16(0x04000130)&0x304)==0;
 if(pressed&&!held){enabled^=1;valid=0;}held=pressed;
 /* SELECT + R + A cycles the capture cadence: every VBlank, every 2nd, every 3rd. */
 unsigned pressed2=(U16(0x04000130)&0x105)==0;
 if(pressed2&&!held2){cadence=cadence>=3?1:cadence+1;}
 held2=pressed2;
 unsigned idle_before=idle_ran,first=idle_first;idle_ran=0;idle_first=0;
 /* Scanlines the game left free before this VBlank: with little or none its frames are heavy (menus opening,
    saving, scene setup), and the tick sends only registers, palette, OAM and ROM replays so it adds no lag. */
 unsigned slack=first?(first-1<IDLE_END?IDLE_END-(first-1):0):0;
 if(!enabled){timer_off();rq_n=0;return;}
 entry_line=U16(0x04000006);
 /* Some rooms poll the link port every frame: only the register is restored, no audit is forced. */
 U16(0x04000134)=0x8030;
 if(skip){skip--;timer_arm();return;}
 skip=cadence-1;
 /* The interrupted code is not the game's WaitForVBlank loop: the game was still working when VBlank began, so it
    is already behind: the tick sends only what fits in a few scanlines. Only a long busy stretch (saving, loading a
    scene) skips three ticks out of four, and gets no idle checks: they would only cost it interrupts. A handler that
    ended late (after scanline 223, or into the next frame) is treated the same way. */
 unsigned busy=irq_lr-0x080008cau>8,late=entry_line<160 || entry_line>=224;
 if(busy){
  if(busy_run<255)busy_run++;
  if(busy_run>LONG_BUSY && (busy_run&3)){skipped++;DEBUG_COUNT(busy_skips++;last_busy_pc=irq_lr;)timer_off();return;}
 }else busy_run=0;
 unsigned heavy=busy || late || slack<HEAVY_SLACK;
 unsigned ie=U16(0x04000200);
 unsigned known_cb=callback==0x080863a5 || callback==0x080bb399 || callback==0x081afcd5;
 mode=!known_cb;
 tick_frame=now;
 key=!valid || since_key>=(feedback?36000u:1800u);
 if(key){
  since_key=0;known[0]=known[1]=0;hot_known=0;sb_known=0;sb_dim=0;
  for(unsigned i=0;i<393;i++)hashes[i]=0;
  mark_all();
 }else if(callback!=vblank_seen){
  /* A scene change: every block is unverified. While the game has no VBlank callback it is between two scenes
     (loading), and the audit waits for the callback that follows instead of restarting at each switch. */
  if(callback)mark_all();
 }else{
  /* Known scenes are followed through the game's copy queues and idle time audits the rest; without idle time an
     unknown scene is audited here, a slice per tick. */
  unsigned n=(known_cb || idle_before)?3:32;
  dirty_mask[0]|=511;
  for(unsigned i=0;i<n;i++){unsigned b=9+audit_cursor;dirty_mask[b>>5]|=BIT(b);other_mask[b>>5]|=BIT(b);if(++audit_cursor==384)audit_cursor=0;}
 }
 dirty_mask[0]|=511;
 vblank_seen=callback;since_key++;
 for(unsigned i=0;i<24;i++)regblock[i]=U32(0x03000818+i*4);
 unsigned pay=FIELDS,records=0,bulk=0;
 unsigned reserve=confirm_requests(),limit=PAY_MAX-reserve;
 unsigned before=records;pay=raster(pay,limit,&records);if(records==before && pay!=FIELDS)records=before;
 /* In a heavy frame even registers, palette and OAM are bounded by the time the game left free last frame. */
 unsigned deadline=starved>=8?2*DEADLINE:DEADLINE;
 if(heavy)deadline=(!busy && !late && slack>12)?slack-8:4;
 /* Liveness: a game that never shows idle time still gets one normal tick every 30 starved ones. */
 if(heavy && starved>=30)deadline=DEADLINE;
 /* A light game leaves many scanlines free: the tick may use half of them (up to 60) instead of leaving them to the
    idle checks, which lose a block's worth of time at the end of every frame. */
 else if(slack>48){unsigned d=slack/2;if(d>60)d=60;if(d>deadline)deadline=d;}
 pay=fill(pay,limit,deadline,0,0,heavy,&records,&bulk);
 unsigned pending=pending_count(dirty_mask,strong_mask);
 if(pending && !bulk){if(starved<255)starved++;}else starved=0;
 for(unsigned i=0;i<13;i++)other_mask[i]&=dirty_mask[i];
 pay=emit_replays(pay,&records);
 fields(0,pending,records,ie,callback);skipped=0;
 emit(0x700,10,0,pay);
 last_words=pay+12;idle_words=0;
 peak_lines=elapsed_lines(U16(0x04000006));
 valid=1;sequence++;DEBUG_COUNT(ticks_sent++;)
 if(++since_feedback>=FEEDBACK_EVERY && !heavy){since_feedback=0;control_slot(now);}
 if(busy)timer_off();else timer_arm();
}
