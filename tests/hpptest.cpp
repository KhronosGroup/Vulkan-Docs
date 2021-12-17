// Copyright 2019-2021 The Khronos Group Inc.
//
// SPDX-License-Identifier: Apache-2.0

#include <vulkan/vulkan.hpp>
int main()
{
    auto const instance_info = vk::InstanceCreateInfo();
    vk::Instance instance;
    vk::createInstance(&instance_info, nullptr, &instance);
}
