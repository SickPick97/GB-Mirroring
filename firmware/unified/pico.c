#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "tusb.h"
/* control.pio assembled words, checked against the independent PIO model. */
static const uint16_t control_code[]={0xe080,0x2080,0xe05f,0x00c5,0x0000,0x0083,0x6030,0x6001,0xe081,0x2000,0x6001,0x2080,0x606e,0x2000,0x6001,0x2080,0x004d,0x2000,0xe080,0x0013};
static const struct pio_program video_control_program={.instructions=control_code,.length=20,.origin=-1};
static uint32_t ring[8192] __attribute__((aligned(32768)));
static const uint16_t instructions[]={0x2000,0x2080,0x4001};
static const struct pio_program program={.instructions=instructions,.length=3,.origin=-1};
static uint csm,coffset;
static bool control_enabled,control_request,control_active;
static uint64_t control_until;
/* Answer of the control slot: word 0 is the number of verdict bits - 1, then "present" (0) and the resync request;
   14 words follow with the PC's verdict (28 16-bit words). Without a fresh verdict they are all ones, which the
   resident rejects by its check word. */
static uint32_t slot_words[15],verdict_words[14];static bool verdict_valid;static uint64_t verdict_time;static int cdma;
static uint32_t control_shift;static unsigned control_bits,control_count;static uint16_t control_packet[24];
static void control_word(uint16_t w){
 for(int i=15;i>=0;i--){
  control_shift=(control_shift<<1)|((w>>i)&1);
  if(control_shift==0xb47e5647){control_count=2;control_bits=0;control_packet[0]=0xb47e;control_packet[1]=0x5647;continue;}
  if(!control_count || ++control_bits<16)continue;
  control_bits=0;control_packet[control_count++]=(uint16_t)control_shift;
  if(control_count!=24)continue;
  control_count=0;
  if(!control_enabled || control_packet[2]!=0x600 || control_packet[3]!=2 || control_packet[6]!=12 || control_packet[11]!=0x5aa5 || (control_packet[22]&255)!=2)continue;
  uint16_t h=65535;uint32_t crc=~0u;const uint8_t *p=(const uint8_t*)control_packet;
  for(unsigned j=4;j<20;j++){h^=(uint16_t)p[j]<<8;for(unsigned k=0;k<8;k++)h=(uint16_t)((h<<1)^((h&0x8000)?0x1021:0));}
  for(unsigned j=24;j<48;j++){crc^=p[j];for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0u-(crc&1))&0xedb88320u);}
  if(h!=control_packet[10] || (~crc)!=(uint32_t)(control_packet[8]|((uint32_t)control_packet[9]<<16)))continue;
  pio_sm_set_enabled(pio0,csm,false);pio_sm_clear_fifos(pio0,csm);pio_sm_restart(pio0,csm);pio_sm_exec(pio0,csm,pio_encode_jmp(coffset));
  bool extended=(control_packet[22]&0x8000)!=0,fresh=extended && verdict_valid && time_us_64()-verdict_time<200000;
  slot_words[0]=(extended?447u:0u)|(control_request?0x20000u:0u);
  for(unsigned j=0;j<14;j++)slot_words[1+j]=fresh?verdict_words[j]:0xffffffffu;
  dma_channel_abort(cdma);dma_channel_set_read_addr(cdma,slot_words,false);dma_channel_set_trans_count(cdma,15,true);
  control_request=false;control_until=time_us_64()+(extended?5000:1500);control_active=true;pio_sm_set_enabled(pio0,csm,true);
 }
}
static uint sm,offset;static int dma;static bool armed;static uint32_t consumed;
static void video_stop(void){pio_sm_set_enabled(pio0,csm,false);dma_channel_abort(cdma);verdict_valid=false;pio_sm_set_consecutive_pindirs(pio0,csm,3,1,false);pio_sm_set_enabled(pio0,sm,false);dma_channel_abort(dma);armed=false;control_enabled=false;control_active=false;control_count=0;}
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
 pio_sm_clear_fifos(pio0,csm);pio_sm_restart(pio0,csm);pio_sm_exec(pio0,csm,pio_encode_jmp(coffset));
}
static void command(const char *s){
 if(!strcmp(s,"BOOT"))boot_start();
 else if(!strcmp(s,"START"))begin_video();
 else if(!strcmp(s,"CONTROL")){if(armed)control_enabled=true;}
 else if(!strcmp(s,"RESYNC")){if(armed)control_request=true;}
 else if(s[0]=='V' && strlen(s)==113){
  /* Verdict from the PC: 28 words as 112 hexadecimal digits, least significant byte first. */
  uint8_t raw[56];bool ok=true;
  for(unsigned i=0;i<112;i++){
   unsigned c=(unsigned char)s[1+i],v=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:16;
   if(v>15){ok=false;break;}
   if(i&1)raw[i>>1]|=(uint8_t)v;else raw[i>>1]=(uint8_t)(v<<4);
  }
  if(ok){memcpy(verdict_words,raw,56);verdict_time=time_us_64();verdict_valid=true;}
 }
 else if(!strcmp(s,"STOP"))release_bus();
 else if(s[0]=='T'){unsigned v=(unsigned)strtoul(s+1,0,10);if(v<=1000000)timing=v;}
 else if(s[0]=='W'){unsigned v=(unsigned)strtoul(s+1,0,10);if(v<=4096){remaining=v*2;half=false;}}
}
int main(void){
 csm=pio_claim_unused_sm(pio0,true);coffset=pio_add_program(pio0,&video_control_program);
 pio_sm_config cc=pio_get_default_sm_config();sm_config_set_wrap(&cc,coffset,coffset+19);sm_config_set_set_pins(&cc,3,1);sm_config_set_out_pins(&cc,3,1);sm_config_set_jmp_pin(&cc,0);sm_config_set_out_shift(&cc,true,true,32);sm_config_set_clkdiv(&cc,16);pio_sm_init(pio0,csm,coffset,&cc);
 sm=pio_claim_unused_sm(pio0,true);offset=pio_add_program(pio0,&program);pio_sm_config c=pio_get_default_sm_config();
 sm_config_set_wrap(&c,offset,offset+2);sm_config_set_in_pins(&c,3);sm_config_set_in_shift(&c,false,true,16);sm_config_set_fifo_join(&c,PIO_FIFO_JOIN_RX);pio_sm_init(pio0,sm,offset,&c);
 cdma=dma_claim_unused_channel(true);{dma_channel_config vc=dma_channel_get_default_config(cdma);channel_config_set_transfer_data_size(&vc,DMA_SIZE_32);channel_config_set_read_increment(&vc,true);channel_config_set_write_increment(&vc,false);channel_config_set_dreq(&vc,pio_get_dreq(pio0,csm,true));dma_channel_configure(cdma,&vc,&pio0->txf[csm],slot_words,0,false);}
 dma=dma_claim_unused_channel(true);dma_channel_config dc=dma_channel_get_default_config(dma);channel_config_set_transfer_data_size(&dc,DMA_SIZE_32);channel_config_set_read_increment(&dc,false);channel_config_set_write_increment(&dc,true);channel_config_set_ring(&dc,true,15);channel_config_set_dreq(&dc,pio_get_dreq(pio0,sm,false));dma_channel_configure(dma,&dc,ring,&pio0->rxf[sm],0,false);
 bsm=pio_claim_unused_sm(pio1,true);boffset=pio_add_program(pio1,&boot_program);c=pio_get_default_sm_config();sm_config_set_wrap(&c,boffset,boffset+26);sm_config_set_set_pins(&c,0,4);sm_config_set_out_pins(&c,3,1);sm_config_set_in_pins(&c,3);sm_config_set_jmp_pin(&c,3);sm_config_set_out_shift(&c,true,false,32);sm_config_set_in_shift(&c,false,false,32);sm_config_set_clkdiv(&c,67.816f);pio_sm_init(pio1,bsm,boffset,&c);release_bus();
 tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
 char cmd[128];unsigned n=0;
 for(;;){
  tud_task();if(control_active && time_us_64()>=control_until){pio_sm_set_enabled(pio0,csm,false);pio_sm_set_consecutive_pindirs(pio0,csm,3,1,false);dma_channel_abort(cdma);control_active=false;}
  if(!tud_cdc_connected()){release_bus();remaining=0;n=0;continue;}
  while(tud_cdc_available()){
   if(remaining && head-tail>=8192)break;
   unsigned ch=(unsigned char)tud_cdc_read_char();
   if(remaining){remaining--;if(!half){lowbyte=ch;half=true;}else{queue[head++&8191]=(uint16_t)(lowbyte|(ch<<8));half=false;}continue;}
   if(ch=='\n'){cmd[n]=0;command(cmd);n=0;}else if(ch!='\r' && n<127)cmd[n++]=(char)ch;
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
  uint16_t bytes[256];for(unsigned i=0;i<count;i++){bytes[i]=(uint16_t)ring[(consumed+i)&8191];control_word(bytes[i]);}
  if(count){consumed+=tud_cdc_write(bytes,count*2)/2;tud_cdc_write_flush();}
 }
}
