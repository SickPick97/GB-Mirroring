/* Index of the 256-byte windows of a cartridge image by the resident's block hash (fast.S hash_begin).

   The game copies much of its graphics from the cartridge unchanged (sprites, some tilesets). A block the GBA
   announces by hash is found here and shown without waiting for its 128 words. Windows start on every 4-byte
   boundary; windows filled with one repeated word are left out. No game content is stored: only hashes and offsets
   computed from the user's own image, in memory. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t a, b, offset; } entry;

static void block_hash(const uint8_t *p, uint32_t *ra, uint32_t *rb) {
    uint32_t a = 0, b = 0;
    for (int g = 0; g < 64; g += 8) {
        for (int i = g; i < g + 8; i++) {
            uint32_t value; memcpy(&value, p + 4 * i, 4);
            a = (a ^ value) * 0x9e3779b1u;
            b = ((b << 7) | (b >> 25)) + value;
        }
        a ^= a >> 15; b += b << 7;
    }
    *ra = a; *rb = b;
}
static int by_hash(const void *x, const void *y) {
    const entry *p = x, *q = y;
    if (p->a != q->a) return p->a < q->a ? -1 : 1;
    if (p->b != q->b) return p->b < q->b ? -1 : 1;
    return p->offset < q->offset ? -1 : p->offset > q->offset;
}
/* Fills out (room for size/4 entries) with the windows sorted by (a, b, offset); returns how many. */
__declspec(dllexport) uint32_t gbm_blocks_index(const uint8_t *rom, uint32_t size, entry *out) {
    uint32_t count = 0;
    if (size < 256) return 0;
    for (uint32_t offset = 0; offset + 256 <= size; offset += 4) {
        const uint8_t *p = rom + offset; int plain = 1;
        for (int i = 4; i < 256; i += 4) if (memcmp(p, p + i, 4)) { plain = 0; break; }
        if (plain) continue;
        block_hash(p, &out[count].a, &out[count].b); out[count].offset = offset; count++;
    }
    qsort(out, count, sizeof(entry), by_hash);
    return count;
}
/* Offset of a window with this hash, or 0xffffffff. */
__declspec(dllexport) uint32_t gbm_blocks_find(const entry *index, uint32_t count, uint32_t a, uint32_t b) {
    uint32_t lo = 0, hi = count;
    while (lo < hi) {
        uint32_t mid = lo + (hi - lo) / 2;
        if (index[mid].a < a || (index[mid].a == a && index[mid].b < b)) lo = mid + 1; else hi = mid;
    }
    return lo < count && index[lo].a == a && index[lo].b == b ? index[lo].offset : 0xffffffffu;
}

/* Palette fades. The game blends each 16-colour palette of its unfaded buffer towards one colour by a step y (0-16):
   c + (((target - c) * y) >> 4) per channel. Given the unfaded block the PC holds (128 colours), the fade colour and
   the hash of the block now on the console, finds the block: one step for all eight palettes, or two steps shared
   among them in any way (palettes not being faded, or loaded while the screen is still dark), or each palette at
   one of: not blended, fully blended, the step the game reports (`hint`). Returns 1 and the block in out, or 0. */
__declspec(dllexport) int gbm_blocks_fade(const uint16_t *unfaded, uint32_t color, uint32_t hint, uint32_t a, uint32_t b, uint16_t *out) {
    static uint16_t t[17][128];
    int R = color & 31, G = color >> 5 & 31, B = color >> 10 & 31;
    for (int y = 0; y <= 16; y++) for (int i = 0; i < 128; i++) {
        int c = unfaded[i], r = c & 31, g = c >> 5 & 31, bl = c >> 10 & 31;
        t[y][i] = (uint16_t)((r + (((R - r) * y) >> 4)) | ((g + (((G - g) * y) >> 4)) << 5) | ((bl + (((B - bl) * y) >> 4)) << 10));
    }
    uint32_t ha, hb;
    for (int y = 0; y <= 16; y++) {
        block_hash((const uint8_t *)t[y], &ha, &hb);
        if (ha == a && hb == b) { memcpy(out, t[y], 256); return 1; }
    }
    uint16_t candidate[128];
    for (int y1 = 0; y1 < 16; y1++) for (int y2 = y1 + 1; y2 <= 16; y2++) for (int mask = 1; mask < 255; mask++) {
        for (int p = 0; p < 8; p++) memcpy(candidate + 16 * p, t[(mask >> p & 1) ? y2 : y1] + 16 * p, 32);
        block_hash((const uint8_t *)candidate, &ha, &hb);
        if (ha == a && hb == b) { memcpy(out, candidate, 256); return 1; }
    }
    if (hint > 16) hint = 16;
    const int three[3] = {0, 16, (int)hint};
    for (int combo = 0; combo < 6561; combo++) {
        int rest = combo;
        for (int p = 0; p < 8; p++) { memcpy(candidate + 16 * p, t[three[rest % 3]] + 16 * p, 32); rest /= 3; }
        block_hash((const uint8_t *)candidate, &ha, &hb);
        if (ha == a && hb == b) { memcpy(out, candidate, 256); return 1; }
    }
    return 0;
}
