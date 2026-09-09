/* GBMirroring Link bench. Runs entirely in EWRAM; no cartridge access.
 * Multiplayer child, BIOS serial interrupt flag polled with CPU IRQ disabled.
 * One next word is prepared per transfer: no whole-packet CRC stall.
 */
#include <stdint.h>
#define REG(a) (*(volatile uint16_t *)(a))
#define VRAM ((volatile uint16_t *)0x06000000)
#define SIOCNT REG(0x04000128)
#define SEND REG(0x0400012a)
#define IF REG(0x04000202)
#include "font.h"

static uint32_t sequence, transfers, errors;
static uint16_t challenge, pending_capture, capturing, chunk;
static uint16_t pos, crc, saved[7];

static uint16_t crc_word(uint16_t c, uint16_t w) {
    /* CRC-16/CCITT-FALSE, low byte of each wire word first. */
    for (unsigned byte=0; byte<2; ++byte) {
        c ^= (uint16_t)((w & 255u) << 8); w >>= 8;
        for (unsigned bit=0; bit<8; ++bit)
            c = (uint16_t)((c << 1) ^ ((c & 0x8000) ? 0x1021 : 0));
    }
    return c;
}
static uint16_t pattern(uint32_t seq, unsigned i) {
    static const uint16_t special[5] = {0, 0xffff, 0xa55a, 0x7fff, 0x8000};
    if (i < 12) return special[i-7];
    uint32_t x = seq ^ (0x9e3779b9u * (i + 1u));
    x ^= x >> 16; x *= 0x45d9f3bu; x ^= x >> 16;
    return (uint16_t)x;
}
static void text(unsigned x, unsigned y, const char *s) {
    for (; *s; ++s, x+=6) {
        const uint8_t *g = 0;
        if (*s >= 'A' && *s <= 'Z') g=letters[*s-'A'];
        if (*s >= '0' && *s <= '9') g=digits[*s-'0'];
        for (unsigned c=0; c<5; ++c)
            for (unsigned r=0; r<7; ++r)
                if (g && (g[c] & (1u<<r))) VRAM[(y+r)*240+x+c]=0x7fff;
    }
}
static void screen(void) {
    REG(0x04000000)=0x0080; /* forced blank while drawing */
    for (unsigned i=0; i<38400; ++i) VRAM[i]=0;
    text(12,8,"GBMIRRORING LINK TEST");
    text(12,22,"GBA RAM TO PC   V020");
    const uint16_t colors[8]={0x7fff,0x03ff,0x7fe0,0x03e0,0x7c1f,0x001f,0x7c00,0};
    for (unsigned y=40; y<105; ++y)
        for (unsigned x=0; x<240; ++x) VRAM[y*240+x]=colors[x/30];
    text(12,116,"LINK ACTIVITY");
    text(12,138,"NO CARTRIDGE REQUIRED");
    REG(0x04000000)=0x0403; /* Mode 3, BG2 */
}
static uint16_t next_word(void) {
    uint16_t w;
    if (pos == 0) {
        if (pending_capture && !capturing) {
            pending_capture=0; capturing=1; chunk=0;
        }
        saved[0]=challenge;
        saved[1]=(uint16_t)(~REG(0x04000130)&0x03ff);
        saved[2]=SIOCNT;
        saved[3]=(uint16_t)transfers; saved[4]=(uint16_t)(transfers>>16);
        saved[5]=(uint16_t)errors; saved[6]=(uint16_t)(errors>>16);
        crc=0xffff;
    }
    uint32_t seq=capturing ? chunk : sequence;
    switch(pos) {
        case 0: w=0xb17e; break;
        case 1: w=0x4d47; break;
        case 2: w=1; break;
        case 3: w=capturing ? 2 : 1; break;
        case 4: w=(uint16_t)seq; break;
        case 5: w=(uint16_t)(seq>>16); break;
        case 6: w=64; break;
        case 71: w=crc; break;
        default: {
            unsigned i=pos-7;
            w=capturing ? VRAM[(unsigned)chunk*64+i]
                        : (i<7 ? saved[i] : pattern(sequence,i));
        }
    }
    if (pos>=2 && pos<71) crc=crc_word(crc,w);
    if (++pos==72) {
        pos=0;
        if (capturing) { if (++chunk==600) capturing=0; }
        else ++sequence;
    }
    return w;
}
int main(void) {
    REG(0x04000208)=0; REG(0x04000200)=0;
    screen();
    REG(0x04000134)=0;
    IF=0xffff;
    SEND=next_word();
    SIOCNT=0x6003; /* multiplayer, 115200, request IF flag, IME remains zero */
    for (;;) {
        if (!(IF & 0x80)) continue;
        uint16_t control=SIOCNT;
        uint16_t incoming=REG(0x04000120);
        IF=0x80;
        ++transfers;
        if (control & 0x40) ++errors;
        if (incoming>=0xd000 && incoming<=0xdfff) challenge=incoming;
        if (incoming==0xc001 && !capturing) pending_capture=1;
        SEND=next_word();
        /* Tiny bounded update, frozen for the entire screenshot transfer. */
        if (!capturing && !pending_capture) {
            unsigned x=12+(transfers & 127u);
            VRAM[127*240+x]=(transfers&128u) ? 0x03e0 : 0x7c00;
        }
    }
}
