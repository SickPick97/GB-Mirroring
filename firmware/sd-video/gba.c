#include <stdint.h>
#include "font.h"
#include "codec.h"
#define R16(a) (*(volatile uint16_t *)(a))
#define VRAM ((volatile uint16_t*)0x06000000)
static uint16_t pixels[38400],encoded[38412],header[12];
extern const uint32_t sd_send_start[],sd_send_end[],sd_send_slow[];
static void (*send_words)(const uint16_t*,unsigned);
static uint32_t ticks(void){uint16_t hi,lo;do{hi=R16(0x04000104);lo=R16(0x04000100);}while(hi!=R16(0x04000104));return ((uint32_t)hi<<16)|lo;}
static void text(unsigned x,unsigned y,const char *s){for(;*s;s++,x+=6){const uint8_t*g=0;if(*s>='A'&&*s<='Z')g=letters[*s-'A'];if(*s>='0'&&*s<='9')g=digits[*s-'0'];for(unsigned c=0;c<5;c++)for(unsigned r=0;r<7;r++)if(g && (g[c]&(1u<<r)))VRAM[(y+r)*240+x+c]=32767;}}
static void render(uint32_t seq,unsigned scene){
 const uint16_t colors[]={0x001f,0x03e0,0x7c00,0x03ff,0x7c1f,0x7fe0,0x7fff,0x2108};
 uint32_t noise=seq+1;
 for(unsigned y=0;y<160;y++)for(unsigned x=0;x<240;x++){
  uint16_t v=0;
  if(y>=30){if(scene==2){noise^=noise<<13;noise^=noise>>17;noise^=noise<<5;v=noise&32767;}
   else if(scene==1)v=colors[((x+seq*3)/12+y/12)&7];
   else{v=colors[x/30];unsigned sx=(seq*4)%216;if(y>=65 && y<89 && x>=sx && x<sx+24)v=0;}}
  VRAM[y*240+x]=v;
 }
 text(6,5,"SD VIDEO V040");text(6,17,scene==0?"B SCENE 0   A RAW":scene==1?"B SCENE 1   A RAW":"B SCENE 2   A RAW");
}
int main(void){
 R16(0x04000208)=0;R16(0x04000200)=0;R16(0x04000134)=0x8000;
 R16(0x04000000)=0x403;for(unsigned i=0;i<38400;i++)VRAM[i]=0;
 text(6,15,"LOAD SD VIDEO UF2");text(6,30,"OPEN PC VIEWER THEN A");
 send_words=(void(*)(const uint16_t*,unsigned))sd_send_start;
 while(!(R16(0x04000130)&1)){}while(R16(0x04000130)&1){}while(!(R16(0x04000130)&1)){}
 R16(0x04000128)=0;R16(0x04000134)=0x8030;
 R16(0x04000100)=0;R16(0x04000104)=0;R16(0x04000106)=0x84;R16(0x04000102)=0x82;
 unsigned scene=0,raw=0,slow=0;uint16_t oldkeys=0;uint32_t seq=0;
 for(;;){uint32_t start=ticks();uint16_t keys=(~R16(0x04000130))&0x203,pressed=keys&~oldkeys;oldkeys=keys;if(pressed&2)scene=(scene+1)%3;if(pressed&1)raw^=1;if(pressed&0x200)slow^=1;send_words=(void(*)(const uint16_t*,unsigned))(slow?sd_send_slow:sd_send_start);
  render(seq,scene);text(130,5,slow?"L SLOW":"L FAST");for(unsigned i=0;i<38400;i++)pixels[i]=VRAM[i];
  uint32_t crc=pixel_crc(pixels,38400);unsigned count=raw?0:encode_pixels(pixels,38400,encoded);
  header[0]=0xb47e;header[1]=0x5647;header[2]=0x400;header[3]=count?1:0;header[4]=seq;header[5]=seq>>16;header[6]=count?count:38400;header[7]=38400;header[8]=crc;header[9]=crc>>16;header[10]=header_crc(header+2,8);header[11]=0x5aa5;
  send_words(header,12);send_words(count?encoded:pixels,header[6]);seq++;
  while((uint32_t)(ticks()-start)<6554){}
 }
}
