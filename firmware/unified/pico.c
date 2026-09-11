#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "tusb.h"
static uint32_t ring[8192] __attribute__((aligned(32768)));
static const uint16_t instructions[]={0x2000,0x2080,0x4001};
static const struct pio_program program={.instructions=instructions,.length=3,.origin=-1};
static uint sm,offset;static int dma;static bool armed;static uint32_t consumed;
static void video_stop(void){pio_sm_set_enabled(pio0,sm,false);dma_channel_abort(dma);armed=false;}
static void video_start(void){video_stop();pio_sm_clear_fifos(pio0,sm);pio_sm_restart(pio0,sm);pio_sm_exec(pio0,sm,pio_encode_jmp(offset));pio_sm_exec(pio0,sm,pio_encode_mov(pio_isr,pio_null));pio0->fdebug=0xffffffff;dma_channel_set_write_addr(dma,ring,false);dma_channel_set_trans_count(dma,0xffffffff,true);consumed=0;armed=true;pio_sm_set_enabled(pio0,sm,true);tud_cdc_write_str("READY SD VIDEO 0.4.0\n");tud_cdc_write_flush();}

/* Multiplayer PIO from the hardware-tested 0.3.7; only one bus owner. */
static const uint16_t boot_code[]={0xe08d,0xe00d,0x0082,0xc001,0xe03e,0x0245,0x80a0,0xa047,0xe02f,0x80a0,0xe00c,0xef04,0x6e01,0x004c,0xef0c,0xe008,0xe085,0xe03f,0x1f53,0x0035,0x00d2,0xf62f,0x4e01,0x0056,0x9020,0xfe0c,0xc000};
static const struct pio_program boot_program={.instructions=boot_code,.length=27,.origin=-1};
static uint bsm,boffset;static bool booting,inflight;static uint32_t timing=3700;
static uint16_t queue[8192];static unsigned head,tail;
static unsigned remaining,lowbyte;static bool half;
static void release_bus(void){
 video_stop();pio_sm_set_enabled(pio1,bsm,false);booting=false;inflight=false;head=tail=0;
 for(unsigned i=0;i<5;i++){gpio_init(i);gpio_set_dir(i,GPIO_IN);gpio_disable_pulls(i);}
}
static void boot_start(void){
 release_bus();timing=3700;pio_sm_clear_fifos(pio1,bsm);pio_sm_restart(pio1,bsm);
 pio_sm_exec(pio1,bsm,pio_encode_jmp(boffset));pio_sm_exec(pio1,bsm,pio_encode_set(pio_y,0));
 for(unsigned i=0;i<4;i++)pio_gpio_init(pio1,i);
 booting=true;pio_sm_set_enabled(pio1,bsm,true);tud_cdc_write_str("READY BOOT 0.6.0\n");tud_cdc_write_flush();
}
static void begin_video(void){
 release_bus();gpio_pull_up(0);gpio_pull_up(3);pio_gpio_init(pio0,0);pio_gpio_init(pio0,3);video_start();
}
static void command(const char *s){
 if(!strcmp(s,"BOOT"))boot_start();
 else if(!strcmp(s,"START"))begin_video();
 else if(!strcmp(s,"STOP"))release_bus();
 else if(s[0]=='T'){unsigned v=(unsigned)strtoul(s+1,0,10);if(v<=1000000)timing=v;}
 else if(s[0]=='W'){unsigned v=(unsigned)strtoul(s+1,0,10);if(v<=4096){remaining=v*2;half=false;}}
}
int main(void){
 sm=pio_claim_unused_sm(pio0,true);offset=pio_add_program(pio0,&program);pio_sm_config c=pio_get_default_sm_config();
 sm_config_set_wrap(&c,offset,offset+2);sm_config_set_in_pins(&c,3);sm_config_set_in_shift(&c,false,true,16);sm_config_set_fifo_join(&c,PIO_FIFO_JOIN_RX);pio_sm_init(pio0,sm,offset,&c);
 dma=dma_claim_unused_channel(true);dma_channel_config dc=dma_channel_get_default_config(dma);channel_config_set_transfer_data_size(&dc,DMA_SIZE_32);channel_config_set_read_increment(&dc,false);channel_config_set_write_increment(&dc,true);channel_config_set_ring(&dc,true,15);channel_config_set_dreq(&dc,pio_get_dreq(pio0,sm,false));dma_channel_configure(dma,&dc,ring,&pio0->rxf[sm],0,false);
 bsm=pio_claim_unused_sm(pio1,true);boffset=pio_add_program(pio1,&boot_program);c=pio_get_default_sm_config();sm_config_set_wrap(&c,boffset,boffset+26);sm_config_set_set_pins(&c,0,4);sm_config_set_out_pins(&c,3,1);sm_config_set_in_pins(&c,3);sm_config_set_jmp_pin(&c,3);sm_config_set_out_shift(&c,true,false,32);sm_config_set_in_shift(&c,false,false,32);sm_config_set_clkdiv(&c,67.816f);pio_sm_init(pio1,bsm,boffset,&c);release_bus();
 tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
 char cmd[32];unsigned n=0;
 for(;;){
  tud_task();if(!tud_cdc_connected()){release_bus();remaining=0;n=0;continue;}
  while(tud_cdc_available()){
   if(remaining && head-tail>=8192)break;
   unsigned ch=(unsigned char)tud_cdc_read_char();
   if(remaining){remaining--;if(!half){lowbyte=ch;half=true;}else{queue[head++&8191]=(uint16_t)(lowbyte|(ch<<8));half=false;}continue;}
   if(ch=='\n'){cmd[n]=0;command(cmd);n=0;}else if(ch!='\r' && n<31)cmd[n++]=(char)ch;
  }
  if(booting){
   if(inflight && !pio_sm_is_rx_fifo_empty(pio1,bsm) && tud_cdc_write_available()>=2){
    uint16_t w=(uint16_t)pio_sm_get(pio1,bsm),r=0;for(unsigned i=0;i<16;i++){r=(uint16_t)((r<<1)|(w&1));w>>=1;}
    tud_cdc_write(&r,2);tud_cdc_write_flush();inflight=false;
   }
   if(!inflight && tail<head){pio_sm_put(pio1,bsm,timing);pio_sm_put(pio1,bsm,queue[tail++&8191]);inflight=true;}
  }
  if(!armed)continue;
  uint32_t produced=0xffffffff-dma_channel_hw_addr(dma)->transfer_count;__dmb();
  if(produced-consumed>8192 || (pio0->fdebug&(1u<<sm))){video_stop();tud_cdc_write_str("\nERROR SD DMA OVERRUN\n");tud_cdc_write_flush();continue;}
  unsigned count=produced-consumed,capacity=tud_cdc_write_available()/2;if(count>capacity)count=capacity;if(count>256)count=256;
  uint16_t bytes[256];for(unsigned i=0;i<count;i++)bytes[i]=(uint16_t)ring[(consumed+i)&8191];
  if(count){consumed+=tud_cdc_write(bytes,count*2)/2;tud_cdc_write_flush();}
 }
}
