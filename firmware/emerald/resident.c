#include <stdint.h>
#define U16(a) (*(volatile uint16_t*)(a))
#define U32(a) (*(volatile uint32_t*)(a))
extern uint32_t original_irq;
extern unsigned scan_next(unsigned,const void*,const void*,uint32_t*);
extern uint8_t fast_begin[],fast_end[],hash_begin[],hash_end[];
static uint32_t hashes[393][2];
uint32_t dirty_mask[13];
static unsigned audit_cursor,feedback;
#define U8(a) (*(volatile uint8_t*)(a))
static uint16_t packet[140];
static uint32_t regblock[64];
static uint32_t sequence,last_vblank,last_capture,since_key,valid,enabled,held;
static uint32_t cursor,changed,active,key,capture_frame;
static uint32_t dictionary[32][2],known[2];
static uint16_t previous_hot[5][128];
static uint32_t hot_known;
static uint32_t capture_ticks,capture_words,peak_lines,optimized=2;
volatile uint32_t visits,entry_line,entry_rcnt;
/* Italian BPEI pointers are checked by the loader. Read only pending copy metadata. */
__attribute__((section(".scheduler"))) static void mark_range(uint32_t address,unsigned size){
 if(address<0x06000000 || address>=0x06018000 || !size)return;
 unsigned end=address+size;if(end<address || end>0x06018000)end=0x06018000;
 unsigned first=9+((address-0x06000000)>>8),last=9+((end-1-0x06000000)>>8);
 for(unsigned b=first;b<=last;b++)dirty_mask[b>>5]|=1u<<(b&31);
}
__attribute__((section(".scheduler"))) void observe(void){
 if(!enabled || !(U16(0x04000200)&U16(0x04000202)&1))return;
 if(!U8(0x03000810)){
  unsigned index=U8(0x03000811);
  for(unsigned n=0;n<128;n++,index=(index+1)&127){
   uint32_t a=0x03000010+index*16;unsigned size=U16(a+8);if(!size)break;
   mark_range(U32(a+4),size);
  }
 }
 if(U8(0x02021834)){
  unsigned count=U8(0x02021835);if(count>64)count=64;
  for(unsigned i=0;i<count;i++){uint32_t a=0x02021838+i*12;mark_range(U32(a+4),U16(a+8));}
 }
}
static uint32_t crc32(const uint16_t *data,unsigned count){
 static const uint32_t table[16]={0,0x1db71064,0x3b6e20c8,0x26d930ac,0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c,0xedb88320,0xf00f9344,0xd6d6a3e8,0xcb61b38c,0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c};
 uint32_t c=~0u;for(unsigned i=0;i<count;i++){c^=data[i];for(unsigned j=0;j<4;j++)c=table[c&15]^(c>>4);}return ~c;
}
static uint16_t crc16(const uint16_t*d,unsigned n){
 static const uint16_t t[16]={0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 uint16_t c=65535;for(unsigned i=0;i<n;i++){unsigned w=d[i];
 for(unsigned j=0;j<2;j++){c^=(w&255)<<8;w>>=8;c=(c<<4)^t[c>>12];c=(c<<4)^t[c>>12];}}
 return c;
}
static void emit(unsigned type,unsigned block,unsigned n){
 packet[0]=0xb47e;packet[1]=0x5647;packet[2]=0x600;packet[3]=type;packet[4]=sequence;packet[5]=sequence>>16;packet[6]=n;packet[7]=block;
 uint32_t c=crc32(packet+12,n);packet[8]=c;packet[9]=c>>16;packet[10]=crc16(packet+2,8);packet[11]=0x5aa5;
 ((void(*)(const uint16_t*,unsigned))fast_begin)(packet,n+12);
}
__attribute__((section(".scheduler"))) static unsigned compress(const volatile uint16_t *src){
 unsigned n=0,i=0;
 while(i<128){unsigned v=src[i],count=1;while(i+count<128 && src[i+count]==v)count++;
  if(n+2>=128)return 128;
  packet[12+n++]=count;packet[12+n++]=v;i+=count;
 }
 return n;
}
/* Local word back-references: bounded work and no persistent graphics copy.
   Only replace the existing encoding when strictly smaller. */
__attribute__((section(".scheduler"))) unsigned compress_lz(const volatile uint16_t *src,unsigned limit){
 uint16_t out[128];int16_t last[64];unsigned n=0,i=0,literal=0;
 for(unsigned k=0;k<64;k++)last[k]=-1;
 while(i<128){
  unsigned value=src[i],slot=(value^(value>>6))&63,length=0;
  int prev=last[slot];last[slot]=i;
  if(prev>=0 && src[prev]==value){while(i+length<128 && src[prev+length]==src[i+length])length++;}
  if(length>=3){
   if(n+1>=limit)return limit;
   out[n++]=0x8000|((length-3)<<7)|(i-(unsigned)prev-1);i+=length;literal=0;
  }else{
   if(n+2>=limit)return limit;
   if(!literal){literal=++n;out[literal-1]=0;}
   out[n++]=value;out[literal-1]++;i++;
  }
 }
 for(unsigned k=0;k<n;k++)packet[12+k]=out[k];
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
 feedback=!a;if(!a && b){valid=0;active=0;}
}
__attribute__((section(".scheduler"))) void tick(void){
 uint32_t now=U32(0x030022e0);if(now==last_vblank)return;last_vblank=now;visits++;
 unsigned pressed=(U16(0x04000130)&0x304)==0;
 if(pressed&&!held){enabled^=1;valid=0;active=0;}held=pressed;
 if(!enabled)return;
 entry_line=U16(0x04000006);entry_rcnt=U16(0x04000134);
 if((entry_rcnt&0xfff3)!=0x8030){
  /* Keep a completed reference across Link reinitialization. Partial
     transactions have already changed sender hashes and need a keyframe. */
  if(active && changed)valid=0;
  active=0;for(unsigned i=0;i<13;i++)dirty_mask[i]=~0u;
 }
 U16(0x04000134)=0x8030;
 if(entry_line<160 || entry_line>=224)return;
 unsigned spent=0;
 if(!active){
  unsigned elapsed=now-last_capture;if(elapsed<3)return;
  last_capture=now;capture_frame=now;cursor=0;changed=0;active=1;capture_ticks=0;capture_words=0;peak_lines=0;
  key=!valid || since_key>=(feedback?3600:120);if(key){since_key=0;known[0]=known[1]=0;hot_known=0;}since_key++;
  if(key || U32(0x030022cc)!=0x080863a5){for(unsigned i=0;i<13;i++)dirty_mask[i]=~0u;}
  else {dirty_mask[0]|=511;for(unsigned i=0;i<(elapsed<6?24u:48u);i++){unsigned b=9+audit_cursor;dirty_mask[b>>5]|=1u<<(b&31);audit_cursor++;if(audit_cursor==384)audit_cursor=0;}}
  packet[12]=key;packet[13]=now;packet[14]=now>>16;emit(0,0,3);spent=15;
  for(unsigned i=0;i<24;i++)regblock[i]=U32(0x03000818+i*4);
  for(unsigned i=24;i<64;i++)regblock[i]=0;
 }
 capture_ticks++;
 while(cursor<393){
  if(U16(0x04000006)>=224 || spent>=140)break;
  uint32_t h[3];unsigned next=scan_next(cursor,regblock,key?0:hashes,h);
  cursor=next&0x7fffffff;if(next&0x80000000 || cursor==393)break;
  unsigned block=cursor;const volatile uint32_t *src=(const volatile uint32_t*)h[2];
  unsigned hot=block==0?0:(block>=5 && block<9?block-4:5);
  unsigned slot=(h[0]^(h[0]>>16))&31,type=1,n=128;
  if(optimized && (known[slot>>5]&(1u<<(slot&31))) && h[0]==dictionary[slot][0] && h[1]==dictionary[slot][1]){type=3;n=1;packet[12]=slot;}
  else {
   if(optimized)n=compress((const volatile uint16_t*)src);
   if(n<128){type=4;}
   else for(unsigned i=0;i<64;i++){uint32_t v=src[i];packet[12+i*2]=v;packet[13+i*2]=v>>16;}
  }
  if(type!=3 && hot<5 && (hot_known&(1u<<hot))){
   const volatile uint16_t *words=(const volatile uint16_t*)src;unsigned changes=0;
   for(unsigned i=0;i<128;i++)changes+=words[i]!=previous_hot[hot][i];
   if(changes+8<n){
    type=5;n=8;for(unsigned i=0;i<8;i++)packet[12+i]=0;
    for(unsigned i=0;i<128;i++)if(words[i]!=previous_hot[hot][i]){packet[12+(i>>4)]|=1u<<(i&15);packet[12+n++]=words[i];}
   }
  }
  if(type!=3 && n>32){unsigned packed=compress_lz((const volatile uint16_t*)src,n);if(packed<n){n=packed;type=6;}}
  if(spent+n+12>155)break;
  emit(type,type==3?block:(slot<<9)|block,n);spent+=n+12;
  hashes[block][0]=h[0];hashes[block][1]=h[1];dictionary[slot][0]=h[0];dictionary[slot][1]=h[1];known[slot>>5]|=1u<<(slot&31);
  if(hot<5){for(unsigned i=0;i<128;i++)previous_hot[hot][i]=((const volatile uint16_t*)src)[i];hot_known|=1u<<hot;}
  dirty_mask[block>>5]&=~(1u<<(block&31));cursor++;changed++;
 }
 capture_words+=spent;
 unsigned end_line=U16(0x04000006),lines=(end_line+228-entry_line)%228;if(lines>peak_lines)peak_lines=lines;
 if(cursor==393 && spent+25<=155){
  packet[12]=capture_frame;packet[13]=capture_frame>>16;packet[14]=changed;packet[15]=(U16(0x040000ba)&0x8000)!=0;
  packet[16]=now;packet[17]=now>>16;packet[18]=capture_ticks;packet[19]=capture_words;packet[20]=capture_words>>16;packet[21]=peak_lines;packet[22]=optimized|(feedback<<8)|1024;packet[23]=visits;
  emit(2,0,12);
  /* Flush the final END bits from a possibly shifted 16-bit RX group. */
  packet[0]=0;((void(*)(const uint16_t*,unsigned))fast_begin)(packet,1);
  valid=1;active=0;sequence++;poll_control();
 }
}
