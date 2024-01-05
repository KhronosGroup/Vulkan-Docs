//% gcc -c -Wall -I. -I../include htest.c

// Copyright 2019-2024 The Khronos Group Inc.
// SPDX-License-Identifier: Apache-2.0

// Simple compilation test for Vulkan headers, including all platform
// headers.
// To allow compilation in environments without one or more platforms, fake
// headers for different platforms are supplied. They provide just the types
// Vulkan platforms require.
// When a new Vulkan platform is defined, the corresponding USE_PLATFORM
// header definition, and any supporting fake platform headers, should be
// defined here, along with a trivial compilation test using a Vulkan type
// or function specific to that platform.

// Enable each platform when vulkan.h is included

#define VK_USE_PLATFORM_ANDROID_KHR         // No headers needed
#define VK_USE_PLATFORM_FUCHSIA             // <zircon/types.h>
#define VK_USE_PLATFORM_GGP                 // <ggp_c/vulkan_types.h>
#define VK_USE_PLATFORM_IOS_MVK             // No headers needed
#define VK_USE_PLATFORM_MACOS_MVK           // No headers needed
#define VK_USE_PLATFORM_METAL_EXT           // No headers needed
#define VK_USE_PLATFORM_VI_NN               // No headers needed
#define VK_USE_PLATFORM_WAYLAND_KHR         // <wayland-client.h>
#define VK_USE_PLATFORM_WIN32_KHR           // <windows.h>
#define VK_USE_PLATFORM_XCB_KHR             // <xcb/xcb.h>
#define VK_USE_PLATFORM_XLIB_KHR            // <X11/Xlib.h>
#define VK_USE_PLATFORM_XLIB_XRANDR_EXT     // <X11/extensions/Xrandr.h>
#define VK_USE_PLATFORM_SCREEN_QNX          // <screen/screen.h>
#define VK_ENABLE_BETA_EXTENSIONS           // No headers needed

#include <vulkan/vulkan.h>

// Check with a type or function from each platform header in turn

VkAndroidSurfaceCreateFlagsKHR          android_flags;
VkImagePipeSurfaceCreateFlagsFUCHSIA    fuchsia_flags;
VkStreamDescriptorSurfaceCreateFlagsGGP ggp_flags;
VkIOSSurfaceCreateFlagsMVK              ios_flags;
VkMacOSSurfaceCreateFlagsMVK            macos_flags;
VkMetalSurfaceCreateFlagsEXT            metal_flags;
VkViSurfaceCreateFlagsNN                vi_flags;
VkWaylandSurfaceCreateFlagsKHR          wayland_flags;
VkWin32SurfaceCreateFlagsKHR            win32_flags;
VkXcbSurfaceCreateFlagsKHR              xcb_flags;
VkXlibSurfaceCreateFlagsKHR             xlib_flags;
VkScreenSurfaceCreateFlagsQNX           screen_flags;

int main(void) {
    VkInstanceCreateInfo instance_info;
    VkInstance instance;

    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    instance_info.pNext = NULL,
    instance_info.flags = 0,
    instance_info.pApplicationInfo = NULL,
    instance_info.enabledLayerCount = 0,
    instance_info.ppEnabledLayerNames = NULL,
    instance_info.enabledExtensionCount = 0,
    instance_info.ppEnabledExtensionNames = NULL,

    vkCreateInstance(&instance_info, NULL, &instance);
    vkDestroyInstance(instance, NULL);

    // Test XLIB_XRANDR_EXT platform, which does not define a new type
    VkResult xrandr_result = vkAcquireXlibDisplayEXT((VkPhysicalDevice)0, (Display *)NULL, (VkDisplayKHR)0);

    (void)xrandr_result;
    return 0;
}
