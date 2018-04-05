/*% gcc -Wall -I.. -c test.c
 * Tiny test to make sure vulkan.h compiles.
 * Should be compiled with one or more platform-specific defines enabled:
 *
 * VK_USE_PLATFORM_ANDROID_KHR
 * VK_USE_PLATFORM_IOS_MVK
 * VK_USE_PLATFORM_MACOS_MVK
 * VK_USE_PLATFORM_MIR_KHR
 * VK_USE_PLATFORM_VI_NN
 * VK_USE_PLATFORM_WAYLAND_KHR
 * VK_USE_PLATFORM_WIN32_KHR
 * VK_USE_PLATFORM_XCB_KHR
 * VK_USE_PLATFORM_XLIB_KHR
 *
 * This relies on the model that all platform extensions go into a
 * corresponding platform-specific header, so their presence can be tested.
 */
#include <stdio.h>
#include "vulkan/vulkan.h"

int main(int ac, const char **av) {
    VkStructureType sType;
    VkResult result;

    // Suppress warnings about unused variables
    (void)sType; (void)result;

    sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
    result = VK_SUBOPTIMAL_KHR;
    result = VK_ERROR_OUT_OF_DATE_KHR;

    printf("VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR = 0x%08x\n",
            (unsigned int)VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR);
    printf("VK_SUBOPTIMAL_KHR = 0x%08x\n",
            (unsigned int)VK_SUBOPTIMAL_KHR);
    printf("VK_ERROR_OUT_OF_DATE_KHR = 0x%08x\n",
            (unsigned int)VK_ERROR_OUT_OF_DATE_KHR);
    printf("VK_PIPELINE_CREATE_VIEW_INDEX_FROM_DEVICE_INDEX_BIT = 0x%08x\n",
            (unsigned int)VK_PIPELINE_CREATE_VIEW_INDEX_FROM_DEVICE_INDEX_BIT);
    printf("VK_PIPELINE_CREATE_VIEW_INDEX_FROM_DEVICE_INDEX_BIT_KHR = 0x%08x\n",
            (unsigned int)VK_PIPELINE_CREATE_VIEW_INDEX_FROM_DEVICE_INDEX_BIT_KHR);

    return 0;
}
