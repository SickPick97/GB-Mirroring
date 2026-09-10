#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "hardware/regs/pio.h"
#include "tusb.h"
#include "rx_program.h"
#include "protocol.h"

#define RING_WORDS 8192u
static uint32_t ring[RING_WORDS] __attribute__((aligned(32768)));
static uint32_t packet[N_WORDS], frame[19200];
static bool seen[75], active, armed;
static uint32_t consumed, buffered, overruns, rate, valid, expected, gaps, duplicates;
static uint32_t crc_errors, pattern_errors, screen_blocks, last_seq, parsed_data;
static uint64_t started, ended, last_progress;
static bool have_seq;
static uint64_t last_diagnostic;
static uint32_t raw_last, raw_first[4], raw_samples, headers;
static int dma_ch;
static uint sm,offset;

static void output(const char *s) {
    uint64_t deadline=time_us_64()+2000000;
    size_t n=strlen(s),pos=0;
    while(pos<n && tud_cdc_connected() && time_us_64()<deadline) {
        tud_task();
        pos+=tud_cdc_write(s+pos,(uint32_t)(n-pos));
        tud_cdc_write_flush();
    }
}
static void stop_rx(void) {
    pio_sm_set_enabled(pio0,sm,false);
    dma_channel_abort(dma_ch);
    armed=false;
}
static void start_rx(void) {
    stop_rx();
    pio_sm_clear_fifos(pio0,sm); pio_sm_restart(pio0,sm);
    pio_sm_exec(pio0,sm,pio_encode_jmp(offset));
    /* Reset shift counter as well as the program counter. */
    pio_sm_exec(pio0,sm,pio_encode_mov(pio_isr,pio_null));
    pio0->fdebug=1u<<(PIO_FDEBUG_RXSTALL_LSB+sm);
    dma_channel_set_write_addr(dma_ch,ring,false);
    dma_channel_set_trans_count(dma_ch,0xffffffff,true);
    consumed=0;buffered=0;overruns=0;active=false;
    crc_errors=0;headers=0;raw_samples=0;raw_last=0;
    memset(raw_first,0,sizeof(raw_first));last_diagnostic=time_us_64();
    pio_sm_set_enabled(pio0,sm,true);armed=true;
    output("{\"event\":\"ready\",\"version\":3,\"firmware\":\"0.3.3\",\"clock_pin\":0,\"data_pin\":3}\n");
}
static void finish(void) {
    uint64_t elapsed=ended>started?ended-started:0;
    unsigned stall=!!(pio0->fdebug&(1u<<(PIO_FDEBUG_RXSTALL_LSB+sm)));
    bool clean=valid==expected && expected==N_PACKETS && !gaps && !duplicates &&
        !crc_errors && !pattern_errors && !overruns && !stall && screen_blocks==75;
    char line[640];
    uint32_t image_crc=0xffffffff;
    for(unsigned i=0;i<19200;++i)image_crc=n_crc_word(image_crc,frame[i]);
    image_crc^=0xffffffff;
    snprintf(line,sizeof(line),"{\"event\":\"result\",\"rate\":%"PRIu32",\"clean\":%s,"
        "\"packets\":%"PRIu32",\"expected\":%"PRIu32",\"crc_errors\":%"PRIu32","
        "\"pattern_errors\":%"PRIu32",\"gaps\":%"PRIu32",\"duplicates\":%"PRIu32","
        "\"dma_overruns\":%"PRIu32",\"pio_stall\":%u,\"payload_bytes\":%"PRIu32","
        "\"elapsed_us\":%"PRIu64",\"screen_blocks\":%"PRIu32",\"screen_crc32\":%"PRIu32"}\n",
        rate,clean?"true":"false",valid,expected,crc_errors,pattern_errors,gaps,duplicates,
        overruns,stall,valid*1024,elapsed,screen_blocks,image_crc);
    output(line);
    if(screen_blocks==75) {
        const uint8_t *bytes=(const uint8_t*)frame;
        const char hex[]="0123456789abcdef";
        for(unsigned block=0;block<300;++block) {
            int len=snprintf(line,sizeof(line),"{\"event\":\"image\",\"rate\":%"PRIu32",\"block\":%u,\"hex\":\"",rate,block);
            for(unsigned i=0;i<256;++i) { uint8_t b=bytes[block*256+i];line[len++]=hex[b>>4];line[len++]=hex[b&15]; }
            memcpy(line+len,"\"}\n",4);output(line);
        }
    }
    output("{\"event\":\"phase_done\"}\n");
    active=false;
}
static void accept_packet(void) {
    uint32_t kind=packet[3],seq=packet[5];
    if(kind==N_BEGIN) {
        if(active) { output("{\"event\":\"error\",\"message\":\"unexpected_begin\"}\n");return; }
        rate=packet[4];expected=packet[7];valid=0;gaps=0;duplicates=0;
        crc_errors=0;pattern_errors=0;screen_blocks=0;have_seq=false;parsed_data=0;
        memset(seen,0,sizeof(seen));started=time_us_64();ended=started;last_progress=started;
        active=true;
        char line[128];snprintf(line,sizeof(line),"{\"event\":\"begin\",\"rate\":%"PRIu32",\"expected\":%"PRIu32"}\n",rate,expected);output(line);
        return;
    }
    if(!active || packet[4]!=rate) return;
    if(kind==N_DATA) {
        if(have_seq) {
            if(seq==last_seq) ++duplicates;
            else if(seq!=last_seq+1) ++gaps;
        } else if(seq!=0) ++gaps;
        have_seq=true;last_seq=seq;++parsed_data;
        bool good=seq<N_PACKETS;
        for(unsigned i=0;i<N_PAYLOAD;++i) if(packet[7+i]!=n_pattern(seq,i))good=false;
        if(good)++valid;else ++pattern_errors;
        ended=time_us_64();
        if(ended-last_progress>1000000) {
            char line[128];snprintf(line,sizeof(line),"{\"event\":\"progress\",\"rate\":%"PRIu32",\"packets\":%"PRIu32"}\n",rate,valid);output(line);last_progress=ended;
        }
    } else if(kind==N_SCREEN) {
        if(seq>=75) { ++pattern_errors;return; }
        if(seen[seq]) { ++duplicates;return; }
        memcpy(frame+seq*256,packet+7,1024);seen[seq]=true;++screen_blocks;
    } else if(kind==N_END) {
        if(seq!=N_PACKETS || packet[7]!=expected || parsed_data!=expected)++gaps;
        finish();
    }
}
static void feed(uint32_t w) {
    raw_last=w;if(raw_samples<4)raw_first[raw_samples++]=w;
    packet[buffered++]=w;
    for(;;) {
        if(buffered<2)return;
        if(packet[0]==N_MAGIC0 && packet[1]==N_MAGIC1) {
            if(buffered<N_WORDS)return;
            uint32_t crc=0xffffffff;
            for(unsigned i=2;i<N_WORDS-1;++i)crc=n_crc_word(crc,packet[i]);
            if(packet[2]==3 && packet[6]==256 && packet[3]>=1 && packet[3]<=4 &&
               (packet[4]==262144 || packet[4]==2097152) && (crc^0xffffffff)==packet[N_WORDS-1]) {
                ++headers;accept_packet();buffered=0;return;
            }
            ++crc_errors;
        }
        --buffered;memmove(packet,packet+1,buffered*4);
    }
}
int main(void) {
    /* All Link pins remain inputs, including GP2: this bench is one-way. */
    for(unsigned i=0;i<5;++i) {gpio_init(i);gpio_set_dir(i,GPIO_IN);gpio_disable_pulls(i);}
    gpio_pull_up(0);gpio_pull_up(3);
    gpio_init(25);gpio_set_dir(25,GPIO_OUT);
    sm=pio_claim_unused_sm(pio0,true);offset=pio_add_program(pio0,&normal_rx_program);
    pio_sm_config config=normal_rx_program_get_default_config(offset);
    sm_config_set_in_pins(&config,3);sm_config_set_in_shift(&config,false,true,32);
    sm_config_set_fifo_join(&config,PIO_FIFO_JOIN_RX);
    pio_gpio_init(pio0,0);pio_gpio_init(pio0,3);
    pio_sm_init(pio0,sm,offset,&config);
    dma_ch=dma_claim_unused_channel(true);
    dma_channel_config dc=dma_channel_get_default_config(dma_ch);
    channel_config_set_transfer_data_size(&dc,DMA_SIZE_32);
    channel_config_set_read_increment(&dc,false);channel_config_set_write_increment(&dc,true);
    channel_config_set_ring(&dc,true,15);channel_config_set_dreq(&dc,pio_get_dreq(pio0,sm,false));
    dma_channel_configure(dma_ch,&dc,ring,&pio0->rxf[sm],0,false);
    tusb_rhport_init_t init={.role=TUSB_ROLE_DEVICE,.speed=TUSB_SPEED_FULL};tusb_init(0,&init);
    char command[32];unsigned command_len=0;
    for(;;) {
        tud_task();
        if(!tud_cdc_connected() && armed)stop_rx();
        while(tud_cdc_available()) {
            char c=(char)tud_cdc_read_char();
            if(c=='\n') {command[command_len]=0;if(!strcmp(command,"START"))start_rx();command_len=0;}
            else if(c!='\r') {if(command_len<sizeof(command)-1)command[command_len++]=c;else command_len=0;}
        }
        if(!armed)continue;
        uint32_t produced=0xffffffff-dma_channel_hw_addr(dma_ch)->transfer_count;
        __dmb();
        if(produced-consumed>RING_WORDS) {++overruns;consumed=produced;buffered=0;output("{\"event\":\"error\",\"message\":\"dma_overrun\"}\n");}
        unsigned budget=512;
        while(consumed<produced && budget--) {uint32_t w=ring[consumed&(RING_WORDS-1)];++consumed;feed(w);}
        if(time_us_64()-last_diagnostic>=2000000) {
            char line[512];
            snprintf(line,sizeof(line),"{\"event\":\"diagnostic\",\"words\":%"PRIu32",\"valid_headers\":%"PRIu32",\"crc_errors\":%"PRIu32",\"pins\":%lu,\"pio_pc\":%u,\"pio_stall\":%u,\"first\":[%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32"],\"last\":%"PRIu32"}\n",
                produced,headers,crc_errors,(unsigned long)(gpio_get_all()&15u),
                pio_sm_get_pc(pio0,sm),!!(pio0->fdebug&(1u<<(PIO_FDEBUG_RXSTALL_LSB+sm))),
                raw_first[0],raw_first[1],raw_first[2],raw_first[3],raw_last);
            output(line);last_diagnostic=time_us_64();
        }
        gpio_put(25,(time_us_64()/250000)&1);
    }
}
