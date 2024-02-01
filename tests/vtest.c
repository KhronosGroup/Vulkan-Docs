// Copyright 2021-2024 The Khronos Group Inc.
// SPDX-License-Identifier: Apache-2.0

// Simple compilation test for external codec headers accompanying the
// Vulkan Video extensions.
// Note that these headers and interfaces are not part of the Vulkan API.
// When a new codec header is defined, it should be included here.

#ifdef VK_NO_STDINT_H
typedef char int8_t;
typedef unsigned char uint8_t;
typedef short int16_t;
typedef unsigned short uint16_t;
typedef int int32_t;
typedef unsigned int uint32_t;
#endif
#ifdef VULKAN_VIDEO_ALL
#include "vk_video/vulkan_video_codecs_common.h"
#include "vk_video/vulkan_video_codec_h264std.h"
#include "vk_video/vulkan_video_codec_h264std_decode.h"
#include "vk_video/vulkan_video_codec_h264std_encode.h"
#include "vk_video/vulkan_video_codec_h265std.h"
#include "vk_video/vulkan_video_codec_h265std_decode.h"
#include "vk_video/vulkan_video_codec_h265std_encode.h"
#include "vk_video/vulkan_video_codec_av1std.h"
#include "vk_video/vulkan_video_codec_av1std_decode.h"
#endif
#ifdef VULKAN_VIDEO_CODECS_COMMON
#include "vk_video/vulkan_video_codecs_common.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H264STD
#include "vk_video/vulkan_video_codec_h264std.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H264STD_DECODE
#include "vk_video/vulkan_video_codec_h264std_decode.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H264STD_ENCODE
#include "vk_video/vulkan_video_codec_h264std_encode.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H265STD
#include "vk_video/vulkan_video_codec_h265std.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H265STD_DECODE
#include "vk_video/vulkan_video_codec_h265std_decode.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_H265STD_ENCODE
#include "vk_video/vulkan_video_codec_h265std_encode.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_AV1STD
#include "vk_video/vulkan_video_codec_av1std.h"
#endif
#ifdef VULKAN_VIDEO_CODEC_AV1STD_DECODE
#include "vk_video/vulkan_video_codec_av1std_decode.h"
#endif

int main(void) {
    return 0;
}
