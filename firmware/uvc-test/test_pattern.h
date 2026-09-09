#pragma once
#include <stdint.h>
#include "video_config.h"

void gbm_render_test_pattern(uint8_t buffer[GBM_FRAME_BYTES], uint32_t frame,
                             uint32_t uptime_s, uint32_t interval_100ns,
                             uint32_t rejected_submissions);

