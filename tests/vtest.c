// Copyright 2021-2023 The Khronos Group Inc.
// SPDX-License-Identifier: Apache-2.0

// Simple compilation test for external codec headers accompanying the
// Vulkan Video extensions.
// Note that these headers and interfaces are not part of the Vulkan API.
// When a new codec header is defined, it should be included here.

#include <stdint.h>
#include "vk_video/vulkan_video_codecs_common.h"
#include "vk_video/vulkan_video_codec_h264std.h"
#include "vk_video/vulkan_video_codec_h264std_decode.h"
#include "vk_video/vulkan_video_codec_h264std_encode.h"
#include "vk_video/vulkan_video_codec_h265std.h"
#include "vk_video/vulkan_video_codec_h265std_decode.h"
#include "vk_video/vulkan_video_codec_h265std_encode.h"

int main(void) {
    return 0;
}
