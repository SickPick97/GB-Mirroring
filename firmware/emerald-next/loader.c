#include <stdint.h>
#include "font.h"
#define R16(a) (*(volatile uint16_t*)(a))
#define R32(a) (*(volatile uint32_t*)(a))
extern uint8_t resident_blob[],resident_blob_end[],stage_blob[],stage_blob_end[];
static void text(unsigned y,const char*s){unsigned x=6;for(;*s;s++,x+=6){const uint8_t*g=0;if(*s>='A'&&*s<='Z')g=letters[*s-'A'];for(unsigned c=0;c<5;c++)for(unsigned r=0;r<7;r++)if(g&&(g[c]&(1<<r)))R16(0x06000000+((y+r)*240+x+c)*2)=32767;}}
static uint32_t boot_crc(void){uint32_t c=~0u;for(unsigned i=0;i<8192;i++){c^=((volatile uint8_t*)0x08000000)[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static int matches(void){return R32(0x080000ac)==0x49455042 && R32(0x08085e70)==0x4809b510 && R32(0x0808dc58)==0x4646b570 && R32(0x080931d4)==0x1c04b570 && R32(0x081aa854)==0xf6feb500 && R32(0x080003ce)==0xfe15f2e0 && R32(0x08001034)==0x03000818 && R32(0x08000c70)==0x03000010 && R32(0x08007484)==0x02021838 && boot_crc()==0x6ee38ad1u;}
int main(void){
 R16(0x04000208)=0;R16(0x04000134)=0x8000;R16(0x04000000)=0x403;
 for(unsigned i=0;i<38400;i++)R16(0x06000000+i*2)=0;
 text(12,"SMERALDO IT EXPERIMENTAL");text(32,"INSERT CART THEN START");text(52,"KEEP PICO CONNECTED");text(72,"PC READY THEN SELECT L R");
 while(1){while(R16(0x04000130)&8){}if(matches())break;text(112,"WRONG CART OR REVISION");while(!(R16(0x04000130)&8)){} }
 for(uint32_t a=0x0203cf80;a<0x02040000;a+=4)R32(a)=0;
 for(unsigned i=0;i<(unsigned)(resident_blob_end-resident_blob);i++)((volatile uint8_t*)0x0203cf80)[i]=resident_blob[i];
 for(unsigned i=0;i<(unsigned)(stage_blob_end-stage_blob);i++)((volatile uint8_t*)0x0203fe00)[i]=stage_blob[i];
 ((void(*)(void))0x0203fe00)();return 0;
}
