/* PIO sequence adapted from Celio linkLayer_pio.c, GBA master variant.
 * See THIRD_PARTY.md. Own bounded measurement and protocol validator. */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "tusb.h"
static const uint16_t code[]={0xe08d,0xe00d,0x0082,0xc001,0xe03e,0x0245,0x80a0,0xa047,0xe02f,0x80a0,0xe00c,0xef04,0x6e01,0x004c,0xef0c,0xe008,0xe085,0xe03f,0x1f53,0x0035,0x00d2,0xf62f,0x4e01,0x0056,0x9020,0xfe0c,0xc000};
static const struct pio_program program={.instructions=code,.length=27,.origin=-1};
static uint sm,offset;
static uint16_t packet[72];
static unsigned buffered,frames,bad_crc,bad_pattern,gaps,echoes;
static uint32_t previous,first_errors,last_errors;
static uint64_t first_packet,last_packet;
static uint16_t reverse16(uint16_t x){uint16_t r=0;for(unsigned i=0;i<16;i++){r=(r<<1)|(x&1);x>>=1;}return r;}
static uint16_t crcword(uint16_t c,uint16_t w){for(unsigned b=0;b<2;b++){c^=(w&255)<<8;w>>=8;for(unsigned i=0;i<8;i++)c=(c<<1)^((c&0x8000)?0x1021:0);}return c;}
static uint16_t pattern(uint32_t seq,unsigned i){const uint16_t v[]={0,65535,0xa55a,0x7fff,0x8000};if(i<12)return v[i-7];uint32_t x=seq^(0x9e3779b9u*(i+1));x^=x>>16;x*=0x45d9f3b;x^=x>>16;return x;}
static void feed(uint16_t word){
 packet[buffered++]=word;
 while(buffered>=2){
  if(packet[0]==0xb17e && packet[1]==0x4d47){
   if(buffered<72)return;
   uint16_t crc=65535;for(unsigned i=2;i<71;i++)crc=crcword(crc,packet[i]);
   if(packet[2]==1 && packet[3]==1 && packet[6]==64 && crc==packet[71]){
    uint32_t seq=packet[4]|((uint32_t)packet[5]<<16);
    uint32_t errs=packet[12]|((uint32_t)packet[13]<<16);
    if(!frames){first_packet=time_us_64();first_errors=errs;}else if(seq!=previous+1)gaps++;
    last_packet=time_us_64();last_errors=errs;previous=seq;frames++;
    if(packet[7]==0xd160)echoes++;
    for(unsigned i=7;i<64;i++)if(packet[7+i]!=pattern(seq,i))bad_pattern++;
    buffered=0;return;
   }
   bad_crc++;
  }
  buffered--;memmove(packet,packet+1,buffered*sizeof(uint16_t));
 }
}
static void output(const char *s){size_t n=strlen(s),p=0;uint64_t until=time_us_64()+2000000;while(p<n && tud_cdc_connected() && time_us_64()<until){tud_task();p+=tud_cdc_write(s+p,n-p);tud_cdc_write_flush();}}
static void stop(void){pio_sm_set_enabled(pio0,sm,false);for(unsigned i=0;i<5;i++){gpio_init(i);gpio_set_dir(i,GPIO_IN);gpio_disable_pulls(i);}}
static bool run(unsigned timing){
 buffered=frames=bad_crc=bad_pattern=gaps=echoes=0;first_packet=last_packet=0;first_errors=last_errors=0;
 pio_sm_clear_fifos(pio0,sm);pio_sm_restart(pio0,sm);pio_sm_exec(pio0,sm,pio_encode_jmp(offset));
 pio_sm_exec(pio0,sm,pio_encode_set(pio_y,0));
 for(unsigned i=0;i<4;i++)pio_gpio_init(pio0,i);
 pio_sm_put(pio0,sm,timing);pio_sm_put(pio0,sm,0xd160);
 pio0->fdebug=0xffffffff;
 uint64_t start=time_us_64();unsigned words=0;bool connected=true;
 pio_sm_set_enabled(pio0,sm,true);
 while(time_us_64()-start<30000000){
  tud_task();if(!tud_cdc_connected()){connected=false;break;}
  if(!pio_sm_is_rx_fifo_empty(pio0,sm)){
   uint16_t w=reverse16((uint16_t)pio_sm_get(pio0,sm));words++;
   /* Refill before validation so CPU processing overlaps next transfer. */
   pio_sm_put(pio0,sm,timing);pio_sm_put(pio0,sm,0xd160);
   feed(w);
  }
 }
 unsigned debug=pio0->fdebug;uint64_t elapsed=time_us_64()-start;stop();
 bool clean=!(debug & ((1u<<sm)|(1u<<(16+sm)))) && connected && frames>=5 && echoes>=2 && !bad_crc && !bad_pattern && !gaps && last_errors==first_errors;
 char line[640];snprintf(line,sizeof(line),"{\"event\":\"result\",\"firmware\":\"0.3.6\",\"timing\":%u,\"clean\":%s,\"words\":%u,\"elapsed_us\":%llu,\"packets\":%u,\"packet_span_us\":%llu,\"verified_payload_bytes\":%u,\"crc_errors\":%u,\"pattern_errors\":%u,\"sequence_errors\":%u,\"echoes\":%u,\"pio_fdebug\":%u,\"gba_serial_errors_delta\":%lu}\n",timing,clean?"true":"false",words,(unsigned long long)elapsed,frames,(unsigned long long)(frames?last_packet-first_packet:0),frames?(frames-1)*128:0,bad_crc,bad_pattern,gaps,echoes,debug,(unsigned long)(last_errors-first_errors));output(line);return clean;
}
int main(void){
 sm=pio_claim_unused_sm(pio0,true);offset=pio_add_program(pio0,&program);
 pio_sm_config c=pio_get_default_sm_config();sm_config_set_wrap(&c,offset,offset+26);
 sm_config_set_set_pins(&c,0,4);sm_config_set_out_pins(&c,3,1);sm_config_set_in_pins(&c,3);sm_config_set_jmp_pin(&c,3);
 sm_config_set_out_shift(&c,true,false,32);sm_config_set_in_shift(&c,false,false,32);sm_config_set_clkdiv(&c,67.816f);
 pio_sm_init(pio0,sm,offset,&c);stop();
 tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
 char command[16];unsigned n=0;
 for(;;){tud_task();while(tud_cdc_available()){char ch=tud_cdc_read_char();if(ch=='\n'){command[n]=0;n=0;if(!strcmp(command,"START")){output("{\"event\":\"begin\",\"firmware\":\"0.3.6\",\"seconds_per_phase\":30}\n");bool ok=run(1000);if(ok)ok=run(125);output(ok?"{\"event\":\"done\",\"clean\":true}\n":"{\"event\":\"done\",\"clean\":false}\n");}}else if(ch!='\r' && n<15)command[n++]=ch;}}
}
