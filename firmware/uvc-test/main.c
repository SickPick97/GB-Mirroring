#include "pico/stdlib.h"
#include "tusb.h"
#include "test_pattern.h"

static uint8_t frame_buffer[GBM_FRAME_BYTES] __attribute__((aligned(4)));
static bool tx_busy;
static bool was_streaming;
static uint32_t completed_frames;
static uint32_t retries;
static uint32_t interval_100ns = GBM_FAST_INTERVAL_100NS;
static uint64_t next_frame_us;

static void stream_reset(void) {
    tx_busy = false;
    was_streaming = false;
    next_frame_us = 0;
}

void tud_mount_cb(void) { stream_reset(); }
void tud_umount_cb(void) { stream_reset(); }

void tud_video_frame_xfer_complete_cb(uint_fast8_t control, uint_fast8_t stream) {
    if (control || stream) return;
    tx_busy = false;
    ++completed_frames;
}

int tud_video_commit_cb(uint_fast8_t control, uint_fast8_t stream,
                       const video_probe_and_commit_control_t *p) {
    if (control || stream || p->bFormatIndex != 1 || p->bFrameIndex != 1 ||
        (p->dwFrameInterval != GBM_FAST_INTERVAL_100NS &&
         p->dwFrameInterval != GBM_SLOW_INTERVAL_100NS))
        return VIDEO_ERROR_INVALID_VALUE_WITHIN_RANGE;
    interval_100ns = p->dwFrameInterval;
    // TinyUSB discards the previous frame on a successful COMMIT.
    stream_reset();
    return VIDEO_ERROR_NONE;
}

static void video_task(void) {
    if (!tud_mounted()) { stream_reset(); return; }
    // Keep ownership of an in-flight buffer during USB suspend.
    if (tud_suspended()) return;
    bool streaming = tud_video_n_streaming(0, 0);
    if (!streaming) { stream_reset(); return; }
    uint64_t now = time_us_64();
    if (!was_streaming) { was_streaming = true; next_frame_us = now; }
    if (tx_busy || now < next_frame_us) return;

    // This single buffer is never modified while TinyUSB is sending it.
    gbm_render_test_pattern(frame_buffer, completed_frames, (uint32_t)(now / 1000000u),
                             interval_100ns, retries);
    tx_busy = true;
    if (!tud_video_n_frame_xfer(0, 0, frame_buffer, sizeof(frame_buffer))) {
        tx_busy = false;
        ++retries;
        next_frame_us = now + 10000u;
        return;
    }
    // No catch-up bursts after a slow host or long pause.
    next_frame_us = now + interval_100ns / 10u;
}

int main(void) {
    // Link pins stay inputs without pulls. No serial traffic, voltage switching or UART.
    for (unsigned pin = 0; pin <= 4; ++pin) {
        gpio_init(pin);
        gpio_set_dir(pin, GPIO_IN);
        gpio_disable_pulls(pin);
    }
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
    const tusb_rhport_init_t init = { .role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_FULL };
    tusb_init(0, &init);
    uint64_t next_led_us = 0;
    bool led = false;
    while (true) {
        tud_task();
        video_task();
        uint64_t now = time_us_64();
        if (now >= next_led_us) {
            led = !led;
            gpio_put(PICO_DEFAULT_LED_PIN, led);
            uint32_t period = tud_suspended() ? 1000000u : was_streaming ? 100000u :
                              tud_mounted() ? 500000u : 250000u;
            next_led_us = now + period;
        }
        tight_loop_contents();
    }
}
