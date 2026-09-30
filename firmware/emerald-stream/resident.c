#include <stdint.h>
#define U16(a) (*(volatile uint16_t*)(a))
#define U32(a) (*(volatile uint32_t*)(a))
extern uint32_t original_irq;
extern unsigned scan_next(unsigned,const void*,const void*,uint32_t*);
extern void sb_sig(const volatile void*,uint16_t*);
extern uint8_t fast_begin[],fast_end[],hash_begin[],hash_end[];
extern unsigned pending_count(const uint32_t*,uint32_t*);
extern unsigned words_equal(const volatile uint32_t*,const volatile uint32_t*,unsigned);
extern void copy16(uint16_t*,const volatile uint16_t*,unsigned);
extern void patch_apply(uint16_t*,const uint16_t*,unsigned);
#ifndef DEADLINE
#define DEADLINE 38
#endif
/* Stream 0.12: one packet per VBlank. Blocks found changed but not yet sent stay
   dirty; the PC learns how many are still outstanding and orders its playout. */
#define FIELDS 6
#define PAY_MAX 224
#define FEEDBACK_EVERY 30
static uint32_t hashes[393];
uint32_t dirty_mask[13];
static uint32_t strong_mask[13],other_mask[13];
#define RQ 12
static uint32_t rq[RQ][3],rp[6][3];static unsigned rq_n,rp_n;
static unsigned audit_cursor,feedback,vblank_seen,bulk_cursor=9,cadence=1,skip,held2;
#define U8(a) (*(volatile uint8_t*)(a))
/* Codecs write straight into the packet; the slack lets a 128-word body be built past the limit and dropped. */
static uint16_t packet[12+PAY_MAX+132];
static uint32_t regblock[64];
static uint32_t sequence,last_vblank,valid,enabled,held;
static uint32_t since_key,since_feedback,changed_total,tick_frame,key;
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
volatile uint32_t visits,entry_line,entry_rcnt,scan_limit=228,scan_stop=393,irq_lr;
static unsigned busy_run,starved,cool,skipped,mode;
__attribute__((section(".scheduler"))) static void mark_all(void){for(unsigned i=0;i<13;i++){dirty_mask[i]=~0u;other_mask[i]=~0u;}}
static inline unsigned elapsed_lines(unsigned line){unsigned d=line+228-entry_line;return d>=228?d-228:d;}
/* Italian BPEI pointers are checked by the loader. Read only pending copy metadata. */
__attribute__((section(".scheduler"))) static void mark_range(uint32_t address,unsigned size,unsigned other){
 if(address<0x06000000 || address>=0x06018000 || !size)return;
 unsigned end=address+size;if(end<address || end>0x06018000)end=0x06018000;
 unsigned first=9+((address-0x06000000)>>8),last=9+((end-1-0x06000000)>>8);
 for(unsigned b=first;b<=last;b++){
  dirty_mask[b>>5]|=1u<<(b&31);strong_mask[b>>5]|=1u<<(b&31);
  if(other)other_mask[b>>5]|=1u<<(b&31);
 }
}
/* A pending copy whose source is the ROM can be replayed by the PC from its own cartridge
   image once the GBA has confirmed that VRAM really holds those ROM bytes. */
__attribute__((section(".scheduler"))) static void request(uint32_t src,uint32_t dest,unsigned size){
 unsigned rom=src>=0x08000000 && src<0x09000000 && !((src|dest|size)&3) && size<=0x2000 && dest>=0x06000000 && dest+size<=0x06018000 && rq_n<RQ;
 if(rom){rq[rq_n][0]=src;rq[rq_n][1]=dest;rq[rq_n][2]=size;rq_n++;}
 mark_range(dest,size,!rom);
}
__attribute__((section(".scheduler"))) void observe(void){
 if(!enabled || !(U16(0x04000200)&U16(0x04000202)&1))return;
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
static const uint32_t crc_table[16] __attribute__((section(".text.crc")))={0,0x1db71064,0x3b6e20c8,0x26d930ac,0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c,0xedb88320,0xf00f9344,0xd6d6a3e8,0xcb61b38c,0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c};
__attribute__((noinline)) static uint32_t crc32(const uint16_t *data,unsigned count){
 uint32_t c=~0u;for(unsigned i=0;i<count;i++){c^=data[i];for(unsigned j=0;j<4;j++)c=crc_table[c&15]^(c>>4);}return ~c;
}
__attribute__((section(".scheduler"))) static uint16_t crc16(const uint16_t*d,unsigned n){
 static const uint16_t t[16]={0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 uint16_t c=65535;for(unsigned i=0;i<n;i++){unsigned w=d[i];
 for(unsigned j=0;j<2;j++){c^=(w&255)<<8;w>>=8;c=(c<<4)^t[c>>12];c=(c<<4)^t[c>>12];}}
 return c;
}
__attribute__((section(".scheduler"))) static void emit(unsigned version,unsigned type,unsigned block,unsigned n){
 packet[0]=0xb47e;packet[1]=0x5647;packet[2]=version;packet[3]=type;packet[4]=sequence;packet[5]=sequence>>16;packet[6]=n;packet[7]=block;
 uint32_t c=crc32(packet+12,n);packet[8]=c;packet[9]=c>>16;packet[10]=crc16(packet+2,8);packet[11]=0x5aa5;
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
  if(rp_n>=5 || (first<=256 && last>=233) || !fits || !words_equal((const volatile uint32_t*)dest,(const volatile uint32_t*)src,size)){
   for(unsigned b=first;b<=last;b++)other_mask[b>>5]|=1u<<(b&31);
   continue;
  }
  rp[rp_n][0]=src;rp[rp_n][1]=dest;rp[rp_n][2]=size;rp_n++;
  for(unsigned b=first;b<=last;b++){
   if(other_mask[b>>5]&(1u<<(b&31)))continue;
   dirty_mask[b>>5]&=~(1u<<(b&31));strong_mask[b>>5]&=~(1u<<(b&31));
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
__attribute__((section(".scheduler"))) void tick(void){
 uint32_t now=U32(0x030022e0);if(now==last_vblank)return;last_vblank=now;visits++;
 unsigned pressed=(U16(0x04000130)&0x304)==0;
 if(pressed&&!held){enabled^=1;valid=0;}held=pressed;
 /* SELECT + R + A cycles the capture cadence: every VBlank, every 2nd, every 3rd. */
 unsigned pressed2=(U16(0x04000130)&0x105)==0;
 if(pressed2&&!held2){cadence=cadence>=3?1:cadence+1;}
 held2=pressed2;
 if(!enabled)return;
 entry_line=U16(0x04000006);entry_rcnt=U16(0x04000134);
 /* Some rooms poll the link port every frame: only the register is restored, no audit is forced. */
 U16(0x04000134)=0x8030;
 if(entry_line<160 || entry_line>=224)return;
 if(skip){skip--;return;}
 if(cool){cool--;skipped++;return;}
 skip=cadence-1;
 /* The interrupted code is outside the BIOS: the game was still working when VBlank began, so it
    is already behind. Give it the whole frame back (at most three times in a row). */
 if(irq_lr>=0x4000 && busy_run<3){busy_run++;skipped++;return;}
 busy_run=0;
 tick_frame=now;
 unsigned pending_key=!valid || since_key>=(feedback?36000u:1800u);
 unsigned callback=U32(0x030022cc);
 key=pending_key;
 if(key){
  since_key=0;known[0]=known[1]=0;hot_known=0;sb_known=0;sb_dim=0;
  for(unsigned i=0;i<393;i++)hashes[i]=0;
  for(unsigned i=0;i<13;i++){dirty_mask[i]=~0u;strong_mask[i]=~0u;other_mask[i]=~0u;}strong_mask[12]=511;
 }else if(callback!=vblank_seen){
  mark_all();
 }else{
  /* The three known callbacks are followed through the game's copy queues; any other scene is only audited,
     a slice of the VRAM per tick, so an unknown scene never costs more than a few scanlines. */
  unsigned known_cb=callback==0x080863a5 || callback==0x080bb399 || callback==0x081afcd5,n=known_cb?3:32;
  mode=!known_cb;
  dirty_mask[0]|=511;
  for(unsigned i=0;i<n;i++){unsigned b=9+audit_cursor;dirty_mask[b>>5]|=1u<<(b&31);other_mask[b>>5]|=1u<<(b&31);audit_cursor++;if(audit_cursor==384)audit_cursor=0;}
 }
 vblank_seen=callback;since_key++;
 for(unsigned i=0;i<24;i++)regblock[i]=U32(0x03000818+i*4);
 unsigned pay=FIELDS,records=0,cursor=0,stage=0,bulk=0;
 unsigned reserve=confirm_requests(),limit=PAY_MAX-reserve;
 for(;;){
  unsigned line=U16(0x04000006);
  /* Registers, palette and OAM are never held back by the time budget (the scan stops at block 9 in that
     stage); bulk blocks are, except that a scene starved for eight ticks in a row gets twice the time. */
  unsigned budget=pay>>3,deadline=(starved>=8 && !bulk)?2*DEADLINE:DEADLINE;
  unsigned gated=stage!=0;
  if(pay+3>limit || (gated && elapsed_lines(line)+budget>=deadline))break;
  scan_limit=gated?(deadline>budget?deadline-budget:1):228;
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
   if(!fit && groups){strong_mask[block>>5]|=1u<<(block&31);break;}
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
   pay+=un+2;records++;bulk++;
   if(partial){
    for(unsigned i=0;i<16;i++){if(colmask&(1u<<i))sb_sigs[k][i]=sig[i];if(rowmask&(1u<<i))sb_sigs[k][16+i]=sig[16+i];}
    sb_dim=(sb_dim&~(3u<<(2*k)))|((colmask?1u:2u)<<(2*k));
   }else{for(unsigned i=0;i<32;i++)sb_sigs[k][i]=sig[i];sb_dim&=~(3u<<(2*k));}
   if(partial){for(unsigned i=0;i<8;i++){unsigned b=first+i;strong_mask[b>>5]|=1u<<(b&31);}break;}
   for(unsigned i=0;i<8;i++){unsigned b=first+i;hashes[b]=bf[i];dirty_mask[b>>5]&=~(1u<<(b&31));strong_mask[b>>5]&=~(1u<<(b&31));}
   cursor=first+8;if(stage)bulk_cursor=cursor>=393?9:cursor;
   continue;
  }
  const volatile uint32_t *src=(const volatile uint32_t*)h[2];
  unsigned hot=block==0?0:(block>=5 && block<9?block-4:5);
  uint32_t fold32=h[0]^(h[1]*0x9e3779b1u);
  unsigned slot=(fold32*2654435761u)>>26,type=1,n=128;
  uint16_t*rec=packet+12+pay,*body=rec+2;
  if((known[slot>>5]&(1u<<(slot&31))) && fold32==dict_fold[slot]){type=3;n=1;body[0]=slot;}
  if(type==1){
   if(hot<5 && (hot_known&(1u<<hot))){n=compress_patch((const volatile uint16_t*)src,(previous_hot+(hot?48+(hot-1)*128:0)),hot?128:48,body);if(n<128)type=5;}
   if(n==128){n=compress((const volatile uint16_t*)src,body);if(n<128)type=4;}
  }
  if(n>=128){type=1;n=128;}
  if(pay+2+n>limit){
   /* Known changed but no room: keep it pending and report it. */
   strong_mask[block>>5]|=1u<<(block&31);
   break;
  }
  if(type==1)copy16(body,(const volatile uint16_t*)src,128);
  rec[0]=type==3?block:(slot<<9)|block;rec[1]=(type<<8)|n;
  pay+=n+2;records++;if(block>=9)bulk++;
  hashes[block]=fold32;dict_fold[slot]=fold32;known[slot>>5]|=1u<<(slot&31);
  if(hot<5){
   uint16_t*previous=previous_hot+(hot?48+(hot-1)*128:0);unsigned count=hot?128u:48u;
   if(type==5)patch_apply(previous,body,count);
   else copy16(previous,(const volatile uint16_t*)src,count);
   hot_known|=1u<<hot;
  }
  dirty_mask[block>>5]&=~(1u<<(block&31));strong_mask[block>>5]&=~(1u<<(block&31));
  cursor=block+1;if(stage)bulk_cursor=cursor>=393?9:cursor;
 }
 /* A layer whose eight blocks are all clean holds exactly what the PC holds: learn its signatures. */
 for(unsigned k=0;k<3;k++)if(!(sb_known&(1u<<k))){
  unsigned first=233+(k<<3),clean=1;
  for(unsigned i=0;i<8;i++){unsigned b=first+i;if(dirty_mask[b>>5]&(1u<<(b&31)))clean=0;}
  if(clean){sb_sig((const volatile void*)(0x06000000+(first-9)*256),sb_sigs[k]);sb_known|=1u<<k;}
 }
 unsigned pending=pending_count(dirty_mask,strong_mask);
 if(pending && !bulk){if(starved<255)starved++;}else starved=0;
 for(unsigned i=0;i<13;i++)other_mask[i]&=dirty_mask[i];
 pay=emit_replays(pay,&records);
 uint16_t*f=packet+12;
 f[0]=key|((U16(0x040000ba)&0x8000)?2:0)|((skipped>7?7:skipped)<<4)|(mode<<11)|(feedback<<8)|(cadence<<9)|0x2000;skipped=0;f[1]=now;f[2]=now>>16;f[3]=pending;f[4]=records;
 f[5]=(peak_lines>255?255:peak_lines)|((last_words>255?255:last_words)<<8);
 emit(0x700,10,0,pay);
 last_words=pay+12;changed_total+=records;
 peak_lines=elapsed_lines(U16(0x04000006));
 /* A tick that ran far past its budget delays the game's next VBlank: back off for a few frames. */
 if(peak_lines>110)cool=6;
 valid=1;sequence++;
 if(++since_feedback>=FEEDBACK_EVERY){since_feedback=0;control_slot(now);}
}
