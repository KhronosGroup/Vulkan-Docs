// Copyright 2019-2023 The Khronos Group Inc.
// SPDX-License-Identifier: Apache-2.0

#include <vulkan/vulkan.hpp>
#include <vulkan/vulkan_video.hpp>
#include <vulkan/vulkan_extension_inspection.hpp>
#include <vulkan/vulkan_format_traits.hpp>
#include <vulkan/vulkan_hash.hpp>
#include <vulkan/vulkan_raii.hpp>
#include <vulkan/vulkan_shared.hpp>
#include <vulkan/vulkan_static_assertions.hpp>

int main()
{
    auto const instance_info = vk::InstanceCreateInfo();
    vk::Instance instance = vk::createInstance(instance_info);
    (void)instance;
}
