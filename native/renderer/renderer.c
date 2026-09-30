/* GBMirroring integration. mGBA renderer sources are unmodified, MPL-2.0. */
#include <mgba/internal/gba/renderers/video-software.h>
#include <mgba/internal/gba/renderers/cache-set.h>
#include <mgba/core/cache-set.h>
#include <mgba/core/log.h>
#include <mgba-util/memory.h>
#define API __declspec(dllexport)
const int GBAVideoObjSizes[16][2]={{8,8},{16,16},{32,32},{64,64},{16,8},{32,8},{32,16},{64,32},{8,16},{8,32},{16,32},{32,64},{0,0},{0,0},{0,0},{0,0}};
struct Context {
 struct GBAVideoSoftwareRenderer video;
 uint16_t palette[512],vram[49152];union GBAOAM oam;
 uint16_t regs[48];mColor pixels[240*160];int initialized;
};
/* Debug tile/map cache is deliberately not installed; renderer's own caches
   remain active. These callbacks must never be called with cache=NULL. */
void GBAVideoCacheWriteVideoRegister(struct mCacheSet*c,uint32_t a,uint16_t v){(void)c;(void)a;(void)v;abort();}
void mCacheSetWriteVRAM(struct mCacheSet*c,uint32_t a){(void)c;(void)a;abort();}
void mCacheSetWritePalette(struct mCacheSet*c,uint32_t a,mColor v){(void)c;(void)a;(void)v;abort();}
int _mLOG_CAT_GBA_VIDEO;
void mLog(int category,enum mLogLevel level,const char*format,...){(void)category;(void)format;if(level==mLOG_FATAL)abort();}
void mappedMemoryFree(void*p,size_t n){(void)n;free(p);}
API void* gbm_create(void){
 struct Context*c=calloc(1,sizeof(*c));if(!c)return NULL;
 GBAVideoSoftwareRendererCreate(&c->video);
 c->video.d.palette=c->palette;c->video.d.vram=c->vram;c->video.d.oam=&c->oam;
 c->video.outputBuffer=c->pixels;c->video.outputBufferStride=240;
 c->video.d.init(&c->video.d);return c;
}
static int render(void*ptr,const uint8_t*gfx,size_t size,unsigned line_reg,const uint16_t*lines,uint16_t*out){
 if(!ptr||!gfx||!out||size!=100608)return 0;
 if(lines&&(line_reg<8||line_reg>=0x60||(line_reg&1)))return 0;
 struct Context*c=ptr;struct GBAVideoRenderer*r=&c->video.d;
 const uint16_t*pal=(const uint16_t*)(gfx+256);const uint16_t*oam=(const uint16_t*)(gfx+1280);
 const uint16_t*vram=(const uint16_t*)(gfx+2304);const uint16_t*regs=(const uint16_t*)gfx;
 for(unsigned i=0;i<512;i++)if(!c->initialized||c->palette[i]!=pal[i]){c->palette[i]=pal[i];r->writePalette(r,i*2,pal[i]);}
 for(unsigned i=0;i<512;i++)if(!c->initialized||c->oam.raw[i]!=oam[i]){c->oam.raw[i]=oam[i];r->writeOAM(r,i*2);}
 for(unsigned i=0;i<49152;i++)if(!c->initialized||c->vram[i]!=vram[i]){c->vram[i]=vram[i];r->writeVRAM(r,i*2);}
 /* Affine reference registers are rewritten every frame to establish the
    supplied snapshot origin; never advance emulator CPU/audio. */
 for(unsigned i=0;i<48;i++)if(i!=2&&i!=3&&i!=39&&i<43){r->writeVideoRegister(r,i*2,regs[i]);c->regs[i]=regs[i];}
 r->finishFrame(r);
 /* Scanline effects: the game's HBlank DMA writes one register before each line; the value for line 0 is set
    before the frame. */
 for(unsigned y=0;y<160;y++){if(lines)r->writeVideoRegister(r,line_reg,lines[y]);r->drawScanline(r,y);}
 for(unsigned i=0;i<38400;i++){
  unsigned v=c->pixels[i];
  out[i]=((v>>11)&31)|((v>>1)&992)|((v&31)<<10);
 }
 r->finishFrame(r);c->initialized=1;return 1;
}
API int gbm_render(void*ptr,const uint8_t*gfx,size_t size,uint16_t*out){return render(ptr,gfx,size,0,NULL,out);}
API int gbm_render_lines(void*ptr,const uint8_t*gfx,size_t size,unsigned line_reg,const uint16_t*lines,uint16_t*out){
 return lines?render(ptr,gfx,size,line_reg,lines,out):0;
}
API void gbm_destroy(void*ptr){if(ptr){struct Context*c=ptr;c->video.d.deinit(&c->video.d);free(c);}}
