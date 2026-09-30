#include <stdint.h>
#include "font.h"
#define R16(a) (*(volatile uint16_t*)(a))
#define R32(a) (*(volatile uint32_t*)(a))
extern uint8_t resident_blob[],resident_blob_end[],stage_blob[],stage_blob_end[];
/* The stage runs once at boot from inside the resident's block-hash table (zeroed at the first keyframe). */
extern const uint32_t stage_address;
extern void sd_send_fast(const uint16_t*,unsigned);
static void text(unsigned y,const char*s){unsigned x=6;for(;*s;s++,x+=6){const uint8_t*g=0;if(*s>='A'&&*s<='Z')g=letters[*s-'A'];for(unsigned c=0;c<5;c++)for(unsigned r=0;r<7;r++)if(g&&(g[c]&(1<<r)))R16(0x06000000+((y+r)*240+x+c)*2)=32767;}}
static uint32_t boot_crc(void){uint32_t c=~0u;for(unsigned i=0;i<8192;i++){c^=((volatile uint8_t*)0x08000000)[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static int matches(void){return R32(0x080000ac)==0x49455042 && R32(0x08085e70)==0x4809b510 && R32(0x0808dc58)==0x4646b570 && R32(0x080931d4)==0x1c04b570 && R32(0x081aa854)==0xf6feb500 && R32(0x080003ce)==0xfe15f2e0 && R32(0x08001034)==0x03000818 && R32(0x08000c70)==0x03000010 && R32(0x08007484)==0x02021838 && boot_crc()==0x6ee38ad1u;}

#ifndef DUMP_CHUNKS
#define DUMP_CHUNKS 65536
#endif
/* One-time cartridge copy: 65536 chunks of 256 bytes, each CRC-protected, paced like the proven RAW sender. */
static uint16_t dump_packet[12+130];
static uint32_t crc32w(const uint16_t*d,unsigned n){
 static const uint32_t t[16]={0,0x1db71064,0x3b6e20c8,0x26d930ac,0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c,0xedb88320,0xf00f9344,0xd6d6a3e8,0xcb61b38c,0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c};
 uint32_t c=~0u;for(unsigned i=0;i<n;i++){c^=d[i];for(unsigned j=0;j<4;j++)c=t[c&15]^(c>>4);}return ~c;
}
static uint16_t crc16w(const uint16_t*d,unsigned n){
 static const uint16_t t[16]={0,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef};
 uint16_t c=65535;for(unsigned i=0;i<n;i++){unsigned w=d[i];for(unsigned j=0;j<2;j++){c^=(w&255)<<8;w>>=8;c=(c<<4)^t[c>>12];c=(c<<4)^t[c>>12];}}return c;
}
static void dump_send(unsigned type,uint32_t seq,unsigned words){
 uint16_t*p=dump_packet;p[0]=0xb47e;p[1]=0x5647;p[2]=0x700;p[3]=type;p[4]=seq;p[5]=seq>>16;p[6]=words;p[7]=0;
 uint32_t c=crc32w(p+12,words);p[8]=c;p[9]=c>>16;p[10]=crc16w(p+2,8);p[11]=0x5aa5;
 sd_send_fast(p,words+12);
}
static void bar(unsigned done,unsigned total){
 unsigned width=(unsigned)(((uint64_t)done*200)/total);
 for(unsigned y=140;y<148;y++)for(unsigned x=20;x<220;x++)R16(0x06000000+(y*240+x)*2)=(x-20<width)?0x03e0:0x2108;
}
static void dump_rom(void){
 R16(0x04000204)=0x4014;R16(0x04000134)=0x8030;
 for(uint32_t chunk=0;chunk<DUMP_CHUNKS;chunk++){
  const volatile uint16_t*rom=(const volatile uint16_t*)(0x08000000+chunk*256);
  uint16_t*payload=dump_packet+12;payload[0]=chunk;payload[1]=chunk>>16;
  for(unsigned i=0;i<128;i++)payload[2+i]=rom[i];
  dump_send(11,chunk,130);
  for(volatile unsigned i=0;i<7700;i++){}
  if(!(chunk&255))bar(chunk,DUMP_CHUNKS);
 }
 dump_packet[12]=(uint16_t)DUMP_CHUNKS;dump_packet[13]=(uint16_t)(DUMP_CHUNKS>>16);dump_send(12,DUMP_CHUNKS,2);
 dump_packet[0]=0;sd_send_fast(dump_packet,1);
 bar(1,1);
}
int main(void){
 R16(0x04000208)=0;R16(0x04000134)=0x8000;R16(0x04000000)=0x403;
 for(unsigned i=0;i<38400;i++)R16(0x06000000+i*2)=0;
 text(12,"SMERALDO IT STREAM");text(32,"INSERT CART THEN START");text(52,"KEEP PICO CONNECTED");text(72,"PC READY THEN SELECT L R");text(92,"A COPIES THE CART ONCE");
 for(;;){
  unsigned keys;
  do keys=R16(0x04000130);while((keys&9)==9);
  unsigned copy=!(keys&1);
  if(matches()){
   if(!copy)break;
   text(112,"COPYING CART");dump_rom();text(124,"DONE RESTART GBA");for(;;){}
  }
  text(112,"WRONG CART OR REVISION");while((R16(0x04000130)&9)!=9){}
 }
 for(uint32_t a=0x0203cf80;a<0x02040000;a+=4)R32(a)=0;
 for(unsigned i=0;i<(unsigned)(resident_blob_end-resident_blob);i++)((volatile uint8_t*)0x0203cf80)[i]=resident_blob[i];
 for(unsigned i=0;i<(unsigned)(stage_blob_end-stage_blob);i++)((volatile uint8_t*)stage_address)[i]=stage_blob[i];
 ((void(*)(void))stage_address)();return 0;
}
