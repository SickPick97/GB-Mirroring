#pragma once
#include "hardware/pio.h"
/* Exact encoding of rx.pio's three instructions. No host C++ toolchain needed.
 * SDK pio_encode_wait_gpio(false,0)=0x2000,
 * pio_encode_wait_gpio(true,0)=0x2080, pio_encode_in(pio_pins,1)=0x4001.
 */
static const uint16_t normal_rx_instructions[]={0x2000,0x2080,0x4001};
static const struct pio_program normal_rx_program={
    .instructions=normal_rx_instructions,.length=3,.origin=-1};
static inline pio_sm_config normal_rx_program_get_default_config(uint offset) {
    pio_sm_config c=pio_get_default_sm_config();
    sm_config_set_wrap(&c,offset,offset+2);
    return c;
}
