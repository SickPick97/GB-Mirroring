/* UVC descriptor layout adapted from TinyUSB's video_capture example.
 * Copyright (c) 2019 Ha Thach (tinyusb.org)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
#include "tusb.h"
#include "pico/unique_id.h"
#include "video_config.h"
#include <string.h>

// CAFE:4020 is TinyUSB's development example ID, not a registered product allocation.
// Kept separate from Celio's 2FE3:000A so its WinUSB binding is not reused.
const tusb_desc_device_t gbm_device_descriptor = {
    .bLength = sizeof(tusb_desc_device_t), .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200, .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON, .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = GBM_USB_VID, .idProduct = GBM_USB_PID, .bcdDevice = 0x0100,
    .iManufacturer = 1, .iProduct = 2, .iSerialNumber = 3, .bNumConfigurations = 1
};

typedef struct TU_ATTR_PACKED {
    tusb_desc_interface_t interface;
    tusb_desc_video_control_header_1itf_t header;
    tusb_desc_video_control_camera_terminal_t camera;
    tusb_desc_video_control_output_terminal_t output;
} control_descriptor_t;

typedef struct TU_ATTR_PACKED {
    tusb_desc_interface_t idle_interface;
    tusb_desc_video_streaming_input_header_1byte_t header;
    tusb_desc_video_format_uncompressed_t format;
    tusb_desc_video_frame_uncompressed_2int_t frame;
    tusb_desc_video_streaming_color_matching_t color;
    tusb_desc_interface_t active_interface;
    tusb_desc_endpoint_t endpoint;
} stream_descriptor_t;

typedef struct TU_ATTR_PACKED {
    tusb_desc_configuration_t config;
    tusb_desc_interface_assoc_t association;
    control_descriptor_t control;
    stream_descriptor_t stream;
} configuration_descriptor_t;

const configuration_descriptor_t gbm_configuration_descriptor = {
    .config = {
        .bLength = sizeof(tusb_desc_configuration_t), .bDescriptorType = TUSB_DESC_CONFIGURATION,
        .wTotalLength = sizeof(configuration_descriptor_t), .bNumInterfaces = 2,
        .bConfigurationValue = 1, .iConfiguration = 0, .bmAttributes = 0x80, .bMaxPower = 50
    },
    .association = {
        .bLength = sizeof(tusb_desc_interface_assoc_t), .bDescriptorType = TUSB_DESC_INTERFACE_ASSOCIATION,
        .bFirstInterface = 0, .bInterfaceCount = 2, .bFunctionClass = TUSB_CLASS_VIDEO,
        .bFunctionSubClass = VIDEO_SUBCLASS_INTERFACE_COLLECTION,
        .bFunctionProtocol = VIDEO_ITF_PROTOCOL_UNDEFINED, .iFunction = 2
    },
    .control = {
        .interface = {
            .bLength = sizeof(tusb_desc_interface_t), .bDescriptorType = TUSB_DESC_INTERFACE,
            .bInterfaceNumber = 0, .bAlternateSetting = 0, .bNumEndpoints = 0,
            .bInterfaceClass = TUSB_CLASS_VIDEO, .bInterfaceSubClass = VIDEO_SUBCLASS_CONTROL,
            .bInterfaceProtocol = VIDEO_ITF_PROTOCOL_15, .iInterface = 4
        },
        .header = {
            .bLength = sizeof(tusb_desc_video_control_header_1itf_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VC_HEADER,
            .bcdUVC = VIDEO_BCD_1_50,
            .wTotalLength = sizeof(control_descriptor_t) - sizeof(tusb_desc_interface_t),
            .dwClockFrequency = 27000000, .bInCollection = 1, .baInterfaceNr = {1}
        },
        .camera = {
            .bLength = sizeof(tusb_desc_video_control_camera_terminal_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VC_INPUT_TERMINAL,
            .bTerminalID = 1, .wTerminalType = VIDEO_ITT_CAMERA, .bAssocTerminal = 0,
            .iTerminal = 0, .wObjectiveFocalLengthMin = 0, .wObjectiveFocalLengthMax = 0,
            .wOcularFocalLength = 0, .bControlSize = 3, .bmControls = {0,0,0}
        },
        .output = {
            .bLength = sizeof(tusb_desc_video_control_output_terminal_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VC_OUTPUT_TERMINAL,
            .bTerminalID = 2, .wTerminalType = VIDEO_TT_STREAMING, .bAssocTerminal = 0,
            .bSourceID = 1, .iTerminal = 0
        }
    },
    .stream = {
        .idle_interface = {
            .bLength = sizeof(tusb_desc_interface_t), .bDescriptorType = TUSB_DESC_INTERFACE,
            .bInterfaceNumber = 1, .bAlternateSetting = 0, .bNumEndpoints = 0,
            .bInterfaceClass = TUSB_CLASS_VIDEO, .bInterfaceSubClass = VIDEO_SUBCLASS_STREAMING,
            .bInterfaceProtocol = VIDEO_ITF_PROTOCOL_15, .iInterface = 5
        },
        .header = {
            .bLength = sizeof(tusb_desc_video_streaming_input_header_1byte_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VS_INPUT_HEADER,
            .bNumFormats = 1,
            .wTotalLength = sizeof(stream_descriptor_t) - 2 * sizeof(tusb_desc_interface_t) - sizeof(tusb_desc_endpoint_t),
            .bEndpointAddress = 0x81, .bmInfo = 0, .bTerminalLink = 2,
            .bStillCaptureMethod = 0, .bTriggerSupport = 0, .bTriggerUsage = 0,
            .bControlSize = 1, .bmaControls = {0}
        },
        .format = {
            .bLength = sizeof(tusb_desc_video_format_uncompressed_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VS_FORMAT_UNCOMPRESSED,
            .bFormatIndex = 1, .bNumFrameDescriptors = 1, .guidFormat = {TUD_VIDEO_GUID_YUY2},
            .bBitsPerPixel = 16, .bDefaultFrameIndex = 1, .bAspectRatioX = 0, .bAspectRatioY = 0,
            .bmInterlaceFlags = 0, .bCopyProtect = 0
        },
        .frame = {
            .bLength = sizeof(tusb_desc_video_frame_uncompressed_2int_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VS_FRAME_UNCOMPRESSED,
            .bFrameIndex = 1, .bmCapabilities = 0, .wWidth = GBM_WIDTH, .wHeight = GBM_HEIGHT,
            .dwMinBitRate = GBM_FRAME_BYTES * 8 * 5, .dwMaxBitRate = GBM_FRAME_BYTES * 8 * 10,
            .dwMaxVideoFrameBufferSize = GBM_FRAME_BYTES, .dwDefaultFrameInterval = GBM_FAST_INTERVAL_100NS,
            .bFrameIntervalType = 2, .dwFrameInterval = {GBM_FAST_INTERVAL_100NS, GBM_SLOW_INTERVAL_100NS}
        },
        .color = {
            .bLength = sizeof(tusb_desc_video_streaming_color_matching_t),
            .bDescriptorType = TUSB_DESC_CS_INTERFACE, .bDescriptorSubType = VIDEO_CS_ITF_VS_COLORFORMAT,
            .bColorPrimaries = VIDEO_COLOR_PRIMARIES_SMPTE170M,
            .bTransferCharacteristics = VIDEO_COLOR_XFER_CH_BT709,
            .bMatrixCoefficients = VIDEO_COLOR_COEF_SMPTE170M
        },
        .active_interface = {
            .bLength = sizeof(tusb_desc_interface_t), .bDescriptorType = TUSB_DESC_INTERFACE,
            .bInterfaceNumber = 1, .bAlternateSetting = 1, .bNumEndpoints = 1,
            .bInterfaceClass = TUSB_CLASS_VIDEO, .bInterfaceSubClass = VIDEO_SUBCLASS_STREAMING,
            .bInterfaceProtocol = VIDEO_ITF_PROTOCOL_15, .iInterface = 5
        },
        .endpoint = {
            .bLength = sizeof(tusb_desc_endpoint_t), .bDescriptorType = TUSB_DESC_ENDPOINT,
            .bEndpointAddress = 0x81, .bmAttributes = {.xfer = TUSB_XFER_ISOCHRONOUS, .sync = 1},
            .wMaxPacketSize = CFG_TUD_VIDEO_STREAMING_EP_BUFSIZE, .bInterval = 1
        }
    }
};

uint8_t const *tud_descriptor_device_cb(void) { return (const uint8_t *)&gbm_device_descriptor; }
uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    return index == 0 ? (const uint8_t *)&gbm_configuration_descriptor : NULL;
}

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t desc[32];
    static char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    static const char *const strings[] = {
        "", "GBMirroring prototype", GBM_USB_PRODUCT, NULL, "Video Control", "Video Streaming"
    };
    size_t count;
    if (index == 0) { desc[1] = 0x0409; count = 1; }
    else {
        if (index >= sizeof(strings) / sizeof(strings[0])) return NULL;
        const char *s = strings[index];
        if (index == 3) {
            if (!serial[0]) pico_get_unique_board_id_string(serial, sizeof(serial));
            s = serial;
        }
        count = strlen(s);
        if (count > 31) count = 31;
        for (size_t i = 0; i < count; ++i) desc[i+1] = (uint8_t)s[i];
    }
    desc[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * count + 2));
    return desc;
}
