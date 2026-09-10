#include <string.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "tusb.h"
static uint32_t ring[8192] __attribute__((aligned(32768)));
static const uint16_t instructions[]={0x2000,0x2080,0x4001};
static const struct pio_program program={.instructions=instructions,.length=3,.origin=-1};
static uint sm,offset;static int dma;static bool armed;static uint32_t consumed;
static void stop(void){pio_sm_set_enabled(pio0,sm,false);dma_channel_abort(dma);armed=false;}
static void start(void){stop();pio_sm_clear_fifos(pio0,sm);pio_sm_restart(pio0,sm);pio_sm_exec(pio0,sm,pio_encode_jmp(offset));pio_sm_exec(pio0,sm,pio_encode_mov(pio_isr,pio_null));pio0->fdebug=0xffffffff;dma_channel_set_write_addr(dma,ring,false);dma_channel_set_trans_count(dma,0xffffffff,true);consumed=0;armed=true;pio_sm_set_enabled(pio0,sm,true);tud_cdc_write_str("READY SD VIDEO 0.4.0\n");tud_cdc_write_flush();}
int main(void){
 for(unsigned i=0;i<5;i++){gpio_init(i);gpio_set_dir(i,GPIO_IN);gpio_disable_pulls(i);}gpio_pull_up(0);gpio_pull_up(3);
 sm=pio_claim_unused_sm(pio0,true);offset=pio_add_program(pio0,&program);pio_sm_config c=pio_get_default_sm_config();sm_config_set_wrap(&c,offset,offset+2);sm_config_set_in_pins(&c,3);sm_config_set_in_shift(&c,false,true,16);sm_config_set_fifo_join(&c,PIO_FIFO_JOIN_RX);pio_gpio_init(pio0,0);pio_gpio_init(pio0,3);pio_sm_init(pio0,sm,offset,&c);
 dma=dma_claim_unused_channel(true);dma_channel_config dc=dma_channel_get_default_config(dma);channel_config_set_transfer_data_size(&dc,DMA_SIZE_32);channel_config_set_read_increment(&dc,false);channel_config_set_write_increment(&dc,true);channel_config_set_ring(&dc,true,15);channel_config_set_dreq(&dc,pio_get_dreq(pio0,sm,false));dma_channel_configure(dma,&dc,ring,&pio0->rxf[sm],0,false);
 tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
 char cmd[16];unsigned n=0;
 for(;;){tud_task();if(!tud_cdc_connected()){if(armed)stop();continue;}
  while(tud_cdc_available()){char ch=tud_cdc_read_char();if(ch=='\n'){cmd[n]=0;if(!strcmp(cmd,"START"))start();else if(!strcmp(cmd,"STOP"))stop();n=0;}else if(ch!='\r'&&n<15)cmd[n++]=ch;}
  if(!armed)continue;
  uint32_t produced=0xffffffff-dma_channel_hw_addr(dma)->transfer_count;__dmb();
  if(produced-consumed>8192 || (pio0->fdebug & (1u<<sm))){stop();tud_cdc_write_str("\nERROR SD DMA OVERRUN\n");tud_cdc_write_flush();continue;}
  unsigned count=produced-consumed,capacity=tud_cdc_write_available()/2;if(count>capacity)count=capacity;if(count>256)count=256;
  uint16_t bytes[256];for(unsigned i=0;i<count;i++)bytes[i]=(uint16_t)ring[(consumed+i)&8191];
  if(count){uint32_t written=tud_cdc_write(bytes,count*2);consumed+=written/2;tud_cdc_write_flush();}
 }
}
