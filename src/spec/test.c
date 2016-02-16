/*% gcc -Wall -I.. -c test.c
 * Tiny test to make sure regenerated vulkan.h compiles.
 * If this code is actually run, it just prints out some enum
 * values and possibly complains about some type conversions.
 *
 * This relies on the model that all extensions go into vulkan.h,
 * so their presence can be tested.
 */
#include <stdio.h>
#include "vulkan/vulkan.h"

int main(int ac, const char **av) {
    VkStructureType sType;
    VkResult result;

    // Supress warnings about unused variables
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

    return 0;
}
