#include "test_pattern.h"
#include <stdio.h>
#include <string.h>

// Five columns per glyph, bit 0 at the top. Text is drawn in neutral YUV.
static const uint8_t letters[26][5] = {
    {0x7e,0x11,0x11,0x11,0x7e}, {0x7f,0x49,0x49,0x49,0x36},
    {0x3e,0x41,0x41,0x41,0x22}, {0x7f,0x41,0x41,0x22,0x1c},
    {0x7f,0x49,0x49,0x49,0x41}, {0x7f,0x09,0x09,0x09,0x01},
    {0x3e,0x41,0x49,0x49,0x7a}, {0x7f,0x08,0x08,0x08,0x7f},
    {0x00,0x41,0x7f,0x41,0x00}, {0x20,0x40,0x41,0x3f,0x01},
    {0x7f,0x08,0x14,0x22,0x41}, {0x7f,0x40,0x40,0x40,0x40},
    {0x7f,0x02,0x0c,0x02,0x7f}, {0x7f,0x04,0x08,0x10,0x7f},
    {0x3e,0x41,0x41,0x41,0x3e}, {0x7f,0x09,0x09,0x09,0x06},
    {0x3e,0x41,0x51,0x21,0x5e}, {0x7f,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7f,0x01,0x01},
    {0x3f,0x40,0x40,0x40,0x3f}, {0x1f,0x20,0x40,0x20,0x1f},
    {0x7f,0x20,0x18,0x20,0x7f}, {0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03}, {0x61,0x51,0x49,0x45,0x43}
};
static const uint8_t digits[10][5] = {
    {0x3e,0x51,0x49,0x45,0x3e}, {0x00,0x42,0x7f,0x40,0x00},
    {0x62,0x51,0x49,0x49,0x46}, {0x22,0x41,0x49,0x49,0x36},
    {0x18,0x14,0x12,0x7f,0x10}, {0x27,0x45,0x45,0x45,0x39},
    {0x3c,0x4a,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1e}
};

static void mono_pixel(uint8_t *b, unsigned x, unsigned y, uint8_t luma) {
    if (x >= GBM_WIDTH || y >= GBM_HEIGHT) return;
    const unsigned pair = (y * GBM_WIDTH + (x & ~1u)) * 2u;
    b[pair + (x & 1u) * 2u] = luma;
    b[pair + 1] = 128;
    b[pair + 3] = 128;
}

static void text(uint8_t *b, unsigned x, unsigned y, const char *s, unsigned scale) {
    for (; *s; ++s, x += 6u * scale) {
        const uint8_t *g = NULL;
        if (*s >= 'A' && *s <= 'Z') g = letters[*s - 'A'];
        if (*s >= '0' && *s <= '9') g = digits[*s - '0'];
        for (unsigned cx = 0; cx < 6; ++cx)
            for (unsigned cy = 0; cy < 8; ++cy)
                for (unsigned dx = 0; dx < scale; ++dx)
                    for (unsigned dy = 0; dy < scale; ++dy)
                        mono_pixel(b, x + cx * scale + dx, y + cy * scale + dy,
                                   g && cx < 5 && cy < 7 && (g[cx] & (1u << cy)) ? 235 : 16);
    }
}

void gbm_render_test_pattern(uint8_t b[GBM_FRAME_BYTES], uint32_t frame,
                             uint32_t uptime_s, uint32_t interval_100ns,
                             uint32_t rejected_submissions) {
    // BT.601 limited-range YUV: white, yellow, cyan, green, magenta, red, blue, black.
    static const uint8_t bars[8][3] = {
        {235,128,128}, {210,16,146}, {170,166,16}, {145,54,34},
        {106,202,222}, {82,90,240}, {41,240,110}, {16,128,128}
    };
    for (unsigned y = 0; y < GBM_HEIGHT; ++y) {
        for (unsigned x = 0; x < GBM_WIDTH; x += 2) {
            unsigned i = (y * GBM_WIDTH + x) * 2u;
            const uint8_t *c = bars[y >= 40 && y < 104 ? x / 30u : 7];
            b[i] = c[0]; b[i+1] = c[1]; b[i+2] = c[0]; b[i+3] = c[2];
        }
    }
    text(b, 12, 5, "GBMIRRORING", 2);
    text(b, 12, 25, "USB TEST   NO GBA VIDEO", 1);
    // Moving marker makes a frozen picture obvious even when the numbers are small.
    unsigned marker = (frame % 30u) * 8u;
    for (unsigned y = 108; y < 114; ++y)
        for (unsigned x = marker; x < marker + 8; ++x) mono_pixel(b, x, y, 235);
    char line[40];
    snprintf(line, sizeof(line), "FRAME %06lu  %lu FPS", (unsigned long)(frame % 1000000u),
             (unsigned long)(interval_100ns ? 10000000u / interval_100ns : 0));
    text(b, 12, 120, line, 1);
    snprintf(line, sizeof(line), "UP %05lu S  RETRY %lu", (unsigned long)(uptime_s % 100000u),
             (unsigned long)(rejected_submissions % 10000u));
    text(b, 12, 134, line, 1);
    text(b, 12, 148, "RP2040   240X160   V010", 1);
}

