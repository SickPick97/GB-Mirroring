#pragma once
#include <stdint.h>
#define N_MAGIC0 0x334d4247u
#define N_MAGIC1 0xc35aa53cu
#define N_WORDS 264u
#define N_PAYLOAD 256u
#define N_PACKETS 1024u
#define N_BEGIN 1u
#define N_DATA 2u
#define N_SCREEN 3u
#define N_END 4u
static inline uint32_t n_crc_word(uint32_t crc, uint32_t w) {
    static const uint32_t lut[16]={0,0x1db71064,0x3b6e20c8,0x26d930ac,
        0x76dc4190,0x6b6b51f4,0x4db26158,0x5005713c,0xedb88320,0xf00f9344,
        0xd6d6a3e8,0xcb61b38c,0x9b64c2b0,0x86d3d2d4,0xa00ae278,0xbdbdf21c};
    for(unsigned i=0;i<8;++i) { crc=(crc>>4)^lut[(crc^w)&15]; w>>=4; }
    return crc;
}
static inline uint32_t n_pattern(uint32_t seq, uint32_t i) {
    static const uint32_t special[8]={0,0xffffffff,0xaaaaaaaa,0x55555555,
        0x80000000,1,0x0000ffff,0xffff0000};
    if(i<8) return special[i];
    uint32_t x=seq^(0x9e3779b9u*(i+1));
    x^=x<<13; x^=x>>17; x^=x<<5;
    return x;
}
