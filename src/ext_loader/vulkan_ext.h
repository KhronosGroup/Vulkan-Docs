#ifndef VULKAN_EXT_H
#define VULKAN_EXT_H

#ifdef __cplusplus
extern "C" {
#endif
/*
** Copyright (c) 2015-2018 The Khronos Group Inc.
**
** Licensed under the Apache License, Version 2.0 (the "License");
** you may not use this file except in compliance with the License.
** You may obtain a copy of the License at
**
**     http://www.apache.org/licenses/LICENSE-2.0
**
** Unless required by applicable law or agreed to in writing, software
** distributed under the License is distributed on an "AS IS" BASIS,
** WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
** See the License for the specific language governing permissions and
** limitations under the License.
*/

/*
** This header is generated from the Khronos Vulkan XML API Registry.
**
*/


/*
** This is a simple extension loader which provides the implementations for the
** extension prototypes declared in vulkan header. It supports loading extensions either
** for a single instance or a single device. Multiple instances are not yet supported.
**
** To use the loader add vulkan_ext.c to your solution and include <vulkan/vulkan_ext.h>.
**
** If your application is using a single instance, but multiple devices callParam
**
** vkExtInitInstance(instance);
**
** after initializing the instance. This way the extension loader will use the loaders
** trampoline functions to call the correct driver for each call. This method is safe
** if your application might use more than one device at the cost of one additional
** indirection, the dispatch table of each dispatchable object.
**
** If your application uses only a single device it's better to use
**
** vkExtInitDevice(device);
**
** once the device has been initialized. This will resolve the function pointers
** upfront and thus removes one indirection for each call into the driver. This *can*
** result in slightly more performance for calling overhead limited cases.
*/

#include <vulkan/vulkan.h>

void vkExtInitInstance(VkInstance instance);
void vkExtInitDevice(VkDevice device);

#ifdef __cplusplus
}
#endif

#endif
