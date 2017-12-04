#ifndef VULKAN_CPPCOMPAT_H_
#define VULKAN_CPPCOMPAT_H_ 1

#ifdef VULKAN_H_
    #error vulkan.h included before vulkan.cppcompat.h! Do not mix use of vulkan.h and vulkan.cppcompat.h!
#endif

#define VK_PIPELINE_SHADER_STAGE_CREATE_INFO_MEMBER_MODULE_NAME shaderModule

#include "vulkan.h"

#endif
