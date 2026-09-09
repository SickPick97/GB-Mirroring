#include <stdint.h>
#include "protocol.h"
#include "font.h"
#define R16(a) (*(volatile uint16_t *)(a))
#define R32(a) (*(volatile uint32_t *)(a))
#define VRAM ((volatile uint16_t *)0x06000000)
static uint32_t packet[N_WORDS];
static uint16_t mode;
static void text(unsigned x,unsigned y,const char *s) {
    for(;*s;++s,x+=6) {
        const uint8_t *g=0;
        if(*s>='A'&&*s<='Z') g=letters[*s-'A'];
        if(*s>='0'&&*s<='9') g=digits[*s-'0'];
        for(unsigned c=0;c<6;++c) for(unsigned r=0;r<8;++r)
            VRAM[(y+r)*240+x+c]=(g&&c<5&&r<7&&(g[c]&(1u<<r)))?0x7fff:0;
    }
}
static void screen(void) {
    R16(0x04000000)=0x80;
    for(unsigned i=0;i<38400;++i) VRAM[i]=0;
    text(6,6,"GBMIRRORING NORMAL V030");
    text(6,20,"GBA TO PICO   NO CARTRIDGE");
    const uint16_t colors[8]={0x7fff,0x03ff,0x7fe0,0x03e0,0x7c1f,0x001f,0x7c00,0};
    for(unsigned y=40;y<104;++y) for(unsigned x=0;x<240;++x) VRAM[y*240+x]=colors[x/30];
    R16(0x04000000)=0x403;
}
static void wait_key(uint16_t mask) {
    while(!(R16(0x04000130)&mask)) {}
    while(R16(0x04000130)&mask) {}
    while(!(R16(0x04000130)&mask)) {}
}
static void send_packet(uint32_t kind,uint32_t rate,uint32_t seq) {
    packet[0]=N_MAGIC0; packet[1]=N_MAGIC1; packet[2]=3;
    packet[3]=kind; packet[4]=rate; packet[5]=seq; packet[6]=N_PAYLOAD;
    for(unsigned i=0;i<N_PAYLOAD;++i) {
        if(kind==N_DATA) packet[7+i]=n_pattern(seq,i);
        else if(kind==N_SCREEN) {
            unsigned p=seq*512+i*2;
            packet[7+i]=(uint32_t)VRAM[p]|((uint32_t)VRAM[p+1]<<16);
        } else packet[7+i]=(i==0)?N_PACKETS:0;
    }
    uint32_t crc=0xffffffff;
    for(unsigned i=2;i<N_WORDS-1;++i) crc=n_crc_word(crc,packet[i]);
    packet[N_WORDS-1]=crc^0xffffffff;
    for(unsigned i=0;i<N_WORDS;++i) {
        R32(0x04000120)=packet[i];
        R16(0x04000128)=mode|0x80;
        while(R16(0x04000128)&0x80) {}
    }
}
static void run(unsigned fast) {
    uint32_t rate=fast?2097152:262144;
    mode=fast?0x100b:0x1009; /* normal32, internal clock, SO high idle */
    R16(0x04000134)=0;
    R16(0x04000128)=mode;
    text(6,116,fast?"TEST 2 MHZ              ":"TEST 256 KHZ            ");
    text(6,132,"SENDING DATA AND SCREEN  ");
    send_packet(N_BEGIN,rate,0);
    for(uint32_t seq=0;seq<N_PACKETS;++seq) send_packet(N_DATA,rate,seq);
    for(uint32_t seq=0;seq<75;++seq) send_packet(N_SCREEN,rate,seq);
    send_packet(N_END,rate,N_PACKETS);
    R16(0x04000128)=0;
    R16(0x04000134)=0x8000; /* release Link while user changes phase */
}
int main(void) {
    R16(0x04000208)=0; R16(0x04000200)=0;
    R16(0x04000134)=0x8000;
    screen();
    for(;;) {
        text(6,116,"LOAD NORMAL UF2 ON PICO  ");
        text(6,132,"PC READY THEN PRESS A   ");
        wait_key(1);
        run(0);
        text(6,116,"WAIT FOR PC RESULT      ");
        text(6,132,"PC OK THEN B FOR 2 MHZ  ");
        wait_key(2);
        run(1);
        text(6,116,"DONE   SEE PC REPORT    ");
        text(6,132,"PRESS START TO REPEAT   ");
        wait_key(8);
    }
}
