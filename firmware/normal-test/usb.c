#include "tusb.h"
#include "pico/unique_id.h"
#include <string.h>
const tusb_desc_device_t normal_device_descriptor={
    .bLength=18,.bDescriptorType=TUSB_DESC_DEVICE,.bcdUSB=0x200,
    .bDeviceClass=TUSB_CLASS_MISC,.bDeviceSubClass=MISC_SUBCLASS_COMMON,
    .bDeviceProtocol=MISC_PROTOCOL_IAD,.bMaxPacketSize0=64,
    .idVendor=0xcafe,.idProduct=0x4021,.bcdDevice=0x0303,
    .iManufacturer=1,.iProduct=2,.iSerialNumber=3,.bNumConfigurations=1};
const uint8_t normal_configuration_descriptor[]={
    TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,100),
    TUD_CDC_DESCRIPTOR(0,4,0x81,8,0x02,0x82,64)};
uint8_t const *tud_descriptor_device_cb(void) { return (const uint8_t*)&normal_device_descriptor; }
uint8_t const *tud_descriptor_configuration_cb(uint8_t index) { (void)index; return normal_configuration_descriptor; }
uint16_t const *tud_descriptor_string_cb(uint8_t index,uint16_t langid) {
    (void)langid;
    static uint16_t desc[48];
    static char serial[2*PICO_UNIQUE_BOARD_ID_SIZE_BYTES+1];
    const char *s=0;
    if(index==0) { desc[0]=0x0304;desc[1]=0x0409;return desc; }
    if(index==1)s="GBMirroring";
    if(index==2)s="GBMirroring Normal Test";
    if(index==3) { pico_get_unique_board_id_string(serial,sizeof(serial));s=serial; }
    if(index==4)s="Normal Link diagnostics";
    if(!s)return 0;
    unsigned n=(unsigned)strlen(s);if(n>47)n=47;
    desc[0]=(uint16_t)(0x0300|((n+1)*2));
    for(unsigned i=0;i<n;++i)desc[i+1]=(uint8_t)s[i];
    return desc;
}
