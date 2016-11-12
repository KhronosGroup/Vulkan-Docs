/*
** Copyright (c) 2015-2016 The Khronos Group Inc.
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

#include <vulkan/vulkan.h>

#ifdef VK_KHR_surface
static PFN_vkDestroySurfaceKHR pfn_vkDestroySurfaceKHR;
void vkDestroySurfaceKHR(
    VkInstance                                  instance,
    VkSurfaceKHR                                surface,
    const VkAllocationCallbacks*                pAllocator)
{
    pfn_vkDestroySurfaceKHR(
        instance,
        surface,
        pAllocator
    );
}

static PFN_vkGetPhysicalDeviceSurfaceSupportKHR pfn_vkGetPhysicalDeviceSurfaceSupportKHR;
VkResult vkGetPhysicalDeviceSurfaceSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex,
    VkSurfaceKHR                                surface,
    VkBool32*                                   pSupported)
{
    return pfn_vkGetPhysicalDeviceSurfaceSupportKHR(
        physicalDevice,
        queueFamilyIndex,
        surface,
        pSupported
    );
}

static PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR pfn_vkGetPhysicalDeviceSurfaceCapabilitiesKHR;
VkResult vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
    VkPhysicalDevice                            physicalDevice,
    VkSurfaceKHR                                surface,
    VkSurfaceCapabilitiesKHR*                   pSurfaceCapabilities)
{
    return pfn_vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
        physicalDevice,
        surface,
        pSurfaceCapabilities
    );
}

static PFN_vkGetPhysicalDeviceSurfaceFormatsKHR pfn_vkGetPhysicalDeviceSurfaceFormatsKHR;
VkResult vkGetPhysicalDeviceSurfaceFormatsKHR(
    VkPhysicalDevice                            physicalDevice,
    VkSurfaceKHR                                surface,
    uint32_t*                                   pSurfaceFormatCount,
    VkSurfaceFormatKHR*                         pSurfaceFormats)
{
    return pfn_vkGetPhysicalDeviceSurfaceFormatsKHR(
        physicalDevice,
        surface,
        pSurfaceFormatCount,
        pSurfaceFormats
    );
}

static PFN_vkGetPhysicalDeviceSurfacePresentModesKHR pfn_vkGetPhysicalDeviceSurfacePresentModesKHR;
VkResult vkGetPhysicalDeviceSurfacePresentModesKHR(
    VkPhysicalDevice                            physicalDevice,
    VkSurfaceKHR                                surface,
    uint32_t*                                   pPresentModeCount,
    VkPresentModeKHR*                           pPresentModes)
{
    return pfn_vkGetPhysicalDeviceSurfacePresentModesKHR(
        physicalDevice,
        surface,
        pPresentModeCount,
        pPresentModes
    );
}

#endif /* VK_KHR_surface */
#ifdef VK_KHR_swapchain
static PFN_vkCreateSwapchainKHR pfn_vkCreateSwapchainKHR;
VkResult vkCreateSwapchainKHR(
    VkDevice                                    device,
    const VkSwapchainCreateInfoKHR*             pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSwapchainKHR*                             pSwapchain)
{
    return pfn_vkCreateSwapchainKHR(
        device,
        pCreateInfo,
        pAllocator,
        pSwapchain
    );
}

static PFN_vkDestroySwapchainKHR pfn_vkDestroySwapchainKHR;
void vkDestroySwapchainKHR(
    VkDevice                                    device,
    VkSwapchainKHR                              swapchain,
    const VkAllocationCallbacks*                pAllocator)
{
    pfn_vkDestroySwapchainKHR(
        device,
        swapchain,
        pAllocator
    );
}

static PFN_vkGetSwapchainImagesKHR pfn_vkGetSwapchainImagesKHR;
VkResult vkGetSwapchainImagesKHR(
    VkDevice                                    device,
    VkSwapchainKHR                              swapchain,
    uint32_t*                                   pSwapchainImageCount,
    VkImage*                                    pSwapchainImages)
{
    return pfn_vkGetSwapchainImagesKHR(
        device,
        swapchain,
        pSwapchainImageCount,
        pSwapchainImages
    );
}

static PFN_vkAcquireNextImageKHR pfn_vkAcquireNextImageKHR;
VkResult vkAcquireNextImageKHR(
    VkDevice                                    device,
    VkSwapchainKHR                              swapchain,
    uint64_t                                    timeout,
    VkSemaphore                                 semaphore,
    VkFence                                     fence,
    uint32_t*                                   pImageIndex)
{
    return pfn_vkAcquireNextImageKHR(
        device,
        swapchain,
        timeout,
        semaphore,
        fence,
        pImageIndex
    );
}

static PFN_vkQueuePresentKHR pfn_vkQueuePresentKHR;
VkResult vkQueuePresentKHR(
    VkQueue                                     queue,
    const VkPresentInfoKHR*                     pPresentInfo)
{
    return pfn_vkQueuePresentKHR(
        queue,
        pPresentInfo
    );
}

#endif /* VK_KHR_swapchain */
#ifdef VK_KHR_display
static PFN_vkGetPhysicalDeviceDisplayPropertiesKHR pfn_vkGetPhysicalDeviceDisplayPropertiesKHR;
VkResult vkGetPhysicalDeviceDisplayPropertiesKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t*                                   pPropertyCount,
    VkDisplayPropertiesKHR*                     pProperties)
{
    return pfn_vkGetPhysicalDeviceDisplayPropertiesKHR(
        physicalDevice,
        pPropertyCount,
        pProperties
    );
}

static PFN_vkGetPhysicalDeviceDisplayPlanePropertiesKHR pfn_vkGetPhysicalDeviceDisplayPlanePropertiesKHR;
VkResult vkGetPhysicalDeviceDisplayPlanePropertiesKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t*                                   pPropertyCount,
    VkDisplayPlanePropertiesKHR*                pProperties)
{
    return pfn_vkGetPhysicalDeviceDisplayPlanePropertiesKHR(
        physicalDevice,
        pPropertyCount,
        pProperties
    );
}

static PFN_vkGetDisplayPlaneSupportedDisplaysKHR pfn_vkGetDisplayPlaneSupportedDisplaysKHR;
VkResult vkGetDisplayPlaneSupportedDisplaysKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    planeIndex,
    uint32_t*                                   pDisplayCount,
    VkDisplayKHR*                               pDisplays)
{
    return pfn_vkGetDisplayPlaneSupportedDisplaysKHR(
        physicalDevice,
        planeIndex,
        pDisplayCount,
        pDisplays
    );
}

static PFN_vkGetDisplayModePropertiesKHR pfn_vkGetDisplayModePropertiesKHR;
VkResult vkGetDisplayModePropertiesKHR(
    VkPhysicalDevice                            physicalDevice,
    VkDisplayKHR                                display,
    uint32_t*                                   pPropertyCount,
    VkDisplayModePropertiesKHR*                 pProperties)
{
    return pfn_vkGetDisplayModePropertiesKHR(
        physicalDevice,
        display,
        pPropertyCount,
        pProperties
    );
}

static PFN_vkCreateDisplayModeKHR pfn_vkCreateDisplayModeKHR;
VkResult vkCreateDisplayModeKHR(
    VkPhysicalDevice                            physicalDevice,
    VkDisplayKHR                                display,
    const VkDisplayModeCreateInfoKHR*           pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkDisplayModeKHR*                           pMode)
{
    return pfn_vkCreateDisplayModeKHR(
        physicalDevice,
        display,
        pCreateInfo,
        pAllocator,
        pMode
    );
}

static PFN_vkGetDisplayPlaneCapabilitiesKHR pfn_vkGetDisplayPlaneCapabilitiesKHR;
VkResult vkGetDisplayPlaneCapabilitiesKHR(
    VkPhysicalDevice                            physicalDevice,
    VkDisplayModeKHR                            mode,
    uint32_t                                    planeIndex,
    VkDisplayPlaneCapabilitiesKHR*              pCapabilities)
{
    return pfn_vkGetDisplayPlaneCapabilitiesKHR(
        physicalDevice,
        mode,
        planeIndex,
        pCapabilities
    );
}

static PFN_vkCreateDisplayPlaneSurfaceKHR pfn_vkCreateDisplayPlaneSurfaceKHR;
VkResult vkCreateDisplayPlaneSurfaceKHR(
    VkInstance                                  instance,
    const VkDisplaySurfaceCreateInfoKHR*        pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateDisplayPlaneSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

#endif /* VK_KHR_display */
#ifdef VK_KHR_display_swapchain
static PFN_vkCreateSharedSwapchainsKHR pfn_vkCreateSharedSwapchainsKHR;
VkResult vkCreateSharedSwapchainsKHR(
    VkDevice                                    device,
    uint32_t                                    swapchainCount,
    const VkSwapchainCreateInfoKHR*             pCreateInfos,
    const VkAllocationCallbacks*                pAllocator,
    VkSwapchainKHR*                             pSwapchains)
{
    return pfn_vkCreateSharedSwapchainsKHR(
        device,
        swapchainCount,
        pCreateInfos,
        pAllocator,
        pSwapchains
    );
}

#endif /* VK_KHR_display_swapchain */
#ifdef VK_KHR_xlib_surface
#ifdef VK_USE_PLATFORM_XLIB_KHR
static PFN_vkCreateXlibSurfaceKHR pfn_vkCreateXlibSurfaceKHR;
VkResult vkCreateXlibSurfaceKHR(
    VkInstance                                  instance,
    const VkXlibSurfaceCreateInfoKHR*           pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateXlibSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

static PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR pfn_vkGetPhysicalDeviceXlibPresentationSupportKHR;
VkBool32 vkGetPhysicalDeviceXlibPresentationSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex,
    Display*                                    dpy,
    VisualID                                    visualID)
{
    return pfn_vkGetPhysicalDeviceXlibPresentationSupportKHR(
        physicalDevice,
        queueFamilyIndex,
        dpy,
        visualID
    );
}

#endif /* VK_USE_PLATFORM_XLIB_KHR */
#endif /* VK_KHR_xlib_surface */
#ifdef VK_KHR_xcb_surface
#ifdef VK_USE_PLATFORM_XCB_KHR
static PFN_vkCreateXcbSurfaceKHR pfn_vkCreateXcbSurfaceKHR;
VkResult vkCreateXcbSurfaceKHR(
    VkInstance                                  instance,
    const VkXcbSurfaceCreateInfoKHR*            pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateXcbSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

static PFN_vkGetPhysicalDeviceXcbPresentationSupportKHR pfn_vkGetPhysicalDeviceXcbPresentationSupportKHR;
VkBool32 vkGetPhysicalDeviceXcbPresentationSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex,
    xcb_connection_t*                           connection,
    xcb_visualid_t                              visual_id)
{
    return pfn_vkGetPhysicalDeviceXcbPresentationSupportKHR(
        physicalDevice,
        queueFamilyIndex,
        connection,
        visual_id
    );
}

#endif /* VK_USE_PLATFORM_XCB_KHR */
#endif /* VK_KHR_xcb_surface */
#ifdef VK_KHR_wayland_surface
#ifdef VK_USE_PLATFORM_WAYLAND_KHR
static PFN_vkCreateWaylandSurfaceKHR pfn_vkCreateWaylandSurfaceKHR;
VkResult vkCreateWaylandSurfaceKHR(
    VkInstance                                  instance,
    const VkWaylandSurfaceCreateInfoKHR*        pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateWaylandSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

static PFN_vkGetPhysicalDeviceWaylandPresentationSupportKHR pfn_vkGetPhysicalDeviceWaylandPresentationSupportKHR;
VkBool32 vkGetPhysicalDeviceWaylandPresentationSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex,
    struct wl_display*                          display)
{
    return pfn_vkGetPhysicalDeviceWaylandPresentationSupportKHR(
        physicalDevice,
        queueFamilyIndex,
        display
    );
}

#endif /* VK_USE_PLATFORM_WAYLAND_KHR */
#endif /* VK_KHR_wayland_surface */
#ifdef VK_KHR_mir_surface
#ifdef VK_USE_PLATFORM_MIR_KHR
static PFN_vkCreateMirSurfaceKHR pfn_vkCreateMirSurfaceKHR;
VkResult vkCreateMirSurfaceKHR(
    VkInstance                                  instance,
    const VkMirSurfaceCreateInfoKHR*            pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateMirSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

static PFN_vkGetPhysicalDeviceMirPresentationSupportKHR pfn_vkGetPhysicalDeviceMirPresentationSupportKHR;
VkBool32 vkGetPhysicalDeviceMirPresentationSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex,
    MirConnection*                              connection)
{
    return pfn_vkGetPhysicalDeviceMirPresentationSupportKHR(
        physicalDevice,
        queueFamilyIndex,
        connection
    );
}

#endif /* VK_USE_PLATFORM_MIR_KHR */
#endif /* VK_KHR_mir_surface */
#ifdef VK_KHR_android_surface
#ifdef VK_USE_PLATFORM_ANDROID_KHR
static PFN_vkCreateAndroidSurfaceKHR pfn_vkCreateAndroidSurfaceKHR;
VkResult vkCreateAndroidSurfaceKHR(
    VkInstance                                  instance,
    const VkAndroidSurfaceCreateInfoKHR*        pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateAndroidSurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

#endif /* VK_USE_PLATFORM_ANDROID_KHR */
#endif /* VK_KHR_android_surface */
#ifdef VK_KHR_win32_surface
#ifdef VK_USE_PLATFORM_WIN32_KHR
static PFN_vkCreateWin32SurfaceKHR pfn_vkCreateWin32SurfaceKHR;
VkResult vkCreateWin32SurfaceKHR(
    VkInstance                                  instance,
    const VkWin32SurfaceCreateInfoKHR*          pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateWin32SurfaceKHR(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

static PFN_vkGetPhysicalDeviceWin32PresentationSupportKHR pfn_vkGetPhysicalDeviceWin32PresentationSupportKHR;
VkBool32 vkGetPhysicalDeviceWin32PresentationSupportKHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t                                    queueFamilyIndex)
{
    return pfn_vkGetPhysicalDeviceWin32PresentationSupportKHR(
        physicalDevice,
        queueFamilyIndex
    );
}

#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_KHR_win32_surface */
#ifdef VK_EXT_debug_report
static PFN_vkCreateDebugReportCallbackEXT pfn_vkCreateDebugReportCallbackEXT;
VkResult vkCreateDebugReportCallbackEXT(
    VkInstance                                  instance,
    const VkDebugReportCallbackCreateInfoEXT*   pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkDebugReportCallbackEXT*                   pCallback)
{
    return pfn_vkCreateDebugReportCallbackEXT(
        instance,
        pCreateInfo,
        pAllocator,
        pCallback
    );
}

static PFN_vkDestroyDebugReportCallbackEXT pfn_vkDestroyDebugReportCallbackEXT;
void vkDestroyDebugReportCallbackEXT(
    VkInstance                                  instance,
    VkDebugReportCallbackEXT                    callback,
    const VkAllocationCallbacks*                pAllocator)
{
    pfn_vkDestroyDebugReportCallbackEXT(
        instance,
        callback,
        pAllocator
    );
}

static PFN_vkDebugReportMessageEXT pfn_vkDebugReportMessageEXT;
void vkDebugReportMessageEXT(
    VkInstance                                  instance,
    VkDebugReportFlagsEXT                       flags,
    VkDebugReportObjectTypeEXT                  objectType,
    uint64_t                                    object,
    size_t                                      location,
    int32_t                                     messageCode,
    const char*                                 pLayerPrefix,
    const char*                                 pMessage)
{
    pfn_vkDebugReportMessageEXT(
        instance,
        flags,
        objectType,
        object,
        location,
        messageCode,
        pLayerPrefix,
        pMessage
    );
}

#endif /* VK_EXT_debug_report */
#ifdef VK_EXT_debug_marker
static PFN_vkDebugMarkerSetObjectTagEXT pfn_vkDebugMarkerSetObjectTagEXT;
VkResult vkDebugMarkerSetObjectTagEXT(
    VkDevice                                    device,
    VkDebugMarkerObjectTagInfoEXT*              pTagInfo)
{
    return pfn_vkDebugMarkerSetObjectTagEXT(
        device,
        pTagInfo
    );
}

static PFN_vkDebugMarkerSetObjectNameEXT pfn_vkDebugMarkerSetObjectNameEXT;
VkResult vkDebugMarkerSetObjectNameEXT(
    VkDevice                                    device,
    VkDebugMarkerObjectNameInfoEXT*             pNameInfo)
{
    return pfn_vkDebugMarkerSetObjectNameEXT(
        device,
        pNameInfo
    );
}

static PFN_vkCmdDebugMarkerBeginEXT pfn_vkCmdDebugMarkerBeginEXT;
void vkCmdDebugMarkerBeginEXT(
    VkCommandBuffer                             commandBuffer,
    VkDebugMarkerMarkerInfoEXT*                 pMarkerInfo)
{
    pfn_vkCmdDebugMarkerBeginEXT(
        commandBuffer,
        pMarkerInfo
    );
}

static PFN_vkCmdDebugMarkerEndEXT pfn_vkCmdDebugMarkerEndEXT;
void vkCmdDebugMarkerEndEXT(
    VkCommandBuffer                             commandBuffer)
{
    pfn_vkCmdDebugMarkerEndEXT(
        commandBuffer
    );
}

static PFN_vkCmdDebugMarkerInsertEXT pfn_vkCmdDebugMarkerInsertEXT;
void vkCmdDebugMarkerInsertEXT(
    VkCommandBuffer                             commandBuffer,
    VkDebugMarkerMarkerInfoEXT*                 pMarkerInfo)
{
    pfn_vkCmdDebugMarkerInsertEXT(
        commandBuffer,
        pMarkerInfo
    );
}

#endif /* VK_EXT_debug_marker */
#ifdef VK_AMD_draw_indirect_count
static PFN_vkCmdDrawIndirectCountAMD pfn_vkCmdDrawIndirectCountAMD;
void vkCmdDrawIndirectCountAMD(
    VkCommandBuffer                             commandBuffer,
    VkBuffer                                    buffer,
    VkDeviceSize                                offset,
    VkBuffer                                    countBuffer,
    VkDeviceSize                                countBufferOffset,
    uint32_t                                    maxDrawCount,
    uint32_t                                    stride)
{
    pfn_vkCmdDrawIndirectCountAMD(
        commandBuffer,
        buffer,
        offset,
        countBuffer,
        countBufferOffset,
        maxDrawCount,
        stride
    );
}

static PFN_vkCmdDrawIndexedIndirectCountAMD pfn_vkCmdDrawIndexedIndirectCountAMD;
void vkCmdDrawIndexedIndirectCountAMD(
    VkCommandBuffer                             commandBuffer,
    VkBuffer                                    buffer,
    VkDeviceSize                                offset,
    VkBuffer                                    countBuffer,
    VkDeviceSize                                countBufferOffset,
    uint32_t                                    maxDrawCount,
    uint32_t                                    stride)
{
    pfn_vkCmdDrawIndexedIndirectCountAMD(
        commandBuffer,
        buffer,
        offset,
        countBuffer,
        countBufferOffset,
        maxDrawCount,
        stride
    );
}

#endif /* VK_AMD_draw_indirect_count */
#ifdef VK_NV_external_memory_capabilities
static PFN_vkGetPhysicalDeviceExternalImageFormatPropertiesNV pfn_vkGetPhysicalDeviceExternalImageFormatPropertiesNV;
VkResult vkGetPhysicalDeviceExternalImageFormatPropertiesNV(
    VkPhysicalDevice                            physicalDevice,
    VkFormat                                    format,
    VkImageType                                 type,
    VkImageTiling                               tiling,
    VkImageUsageFlags                           usage,
    VkImageCreateFlags                          flags,
    VkExternalMemoryHandleTypeFlagsNV           externalHandleType,
    VkExternalImageFormatPropertiesNV*          pExternalImageFormatProperties)
{
    return pfn_vkGetPhysicalDeviceExternalImageFormatPropertiesNV(
        physicalDevice,
        format,
        type,
        tiling,
        usage,
        flags,
        externalHandleType,
        pExternalImageFormatProperties
    );
}

#endif /* VK_NV_external_memory_capabilities */
#ifdef VK_NV_external_memory_win32
#ifdef VK_USE_PLATFORM_WIN32_KHR
static PFN_vkGetMemoryWin32HandleNV pfn_vkGetMemoryWin32HandleNV;
VkResult vkGetMemoryWin32HandleNV(
    VkDevice                                    device,
    VkDeviceMemory                              memory,
    VkExternalMemoryHandleTypeFlagsNV           handleType,
    HANDLE*                                     pHandle)
{
    return pfn_vkGetMemoryWin32HandleNV(
        device,
        memory,
        handleType,
        pHandle
    );
}

#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_NV_external_memory_win32 */

void vkExtInitInstance(VkInstance instance)
{
#ifdef VK_KHR_surface
    pfn_vkDestroySurfaceKHR = (PFN_vkDestroySurfaceKHR)vkGetInstanceProcAddr(instance, "vkDestroySurfaceKHR");
    pfn_vkGetPhysicalDeviceSurfaceSupportKHR = (PFN_vkGetPhysicalDeviceSurfaceSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceSupportKHR");
    pfn_vkGetPhysicalDeviceSurfaceCapabilitiesKHR = (PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
    pfn_vkGetPhysicalDeviceSurfaceFormatsKHR = (PFN_vkGetPhysicalDeviceSurfaceFormatsKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceFormatsKHR");
    pfn_vkGetPhysicalDeviceSurfacePresentModesKHR = (PFN_vkGetPhysicalDeviceSurfacePresentModesKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfacePresentModesKHR");
#endif /* VK_KHR_surface */
#ifdef VK_KHR_swapchain
    pfn_vkCreateSwapchainKHR = (PFN_vkCreateSwapchainKHR)vkGetInstanceProcAddr(instance, "vkCreateSwapchainKHR");
    pfn_vkDestroySwapchainKHR = (PFN_vkDestroySwapchainKHR)vkGetInstanceProcAddr(instance, "vkDestroySwapchainKHR");
    pfn_vkGetSwapchainImagesKHR = (PFN_vkGetSwapchainImagesKHR)vkGetInstanceProcAddr(instance, "vkGetSwapchainImagesKHR");
    pfn_vkAcquireNextImageKHR = (PFN_vkAcquireNextImageKHR)vkGetInstanceProcAddr(instance, "vkAcquireNextImageKHR");
    pfn_vkQueuePresentKHR = (PFN_vkQueuePresentKHR)vkGetInstanceProcAddr(instance, "vkQueuePresentKHR");
#endif /* VK_KHR_swapchain */
#ifdef VK_KHR_display
    pfn_vkGetPhysicalDeviceDisplayPropertiesKHR = (PFN_vkGetPhysicalDeviceDisplayPropertiesKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceDisplayPropertiesKHR");
    pfn_vkGetPhysicalDeviceDisplayPlanePropertiesKHR = (PFN_vkGetPhysicalDeviceDisplayPlanePropertiesKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceDisplayPlanePropertiesKHR");
    pfn_vkGetDisplayPlaneSupportedDisplaysKHR = (PFN_vkGetDisplayPlaneSupportedDisplaysKHR)vkGetInstanceProcAddr(instance, "vkGetDisplayPlaneSupportedDisplaysKHR");
    pfn_vkGetDisplayModePropertiesKHR = (PFN_vkGetDisplayModePropertiesKHR)vkGetInstanceProcAddr(instance, "vkGetDisplayModePropertiesKHR");
    pfn_vkCreateDisplayModeKHR = (PFN_vkCreateDisplayModeKHR)vkGetInstanceProcAddr(instance, "vkCreateDisplayModeKHR");
    pfn_vkGetDisplayPlaneCapabilitiesKHR = (PFN_vkGetDisplayPlaneCapabilitiesKHR)vkGetInstanceProcAddr(instance, "vkGetDisplayPlaneCapabilitiesKHR");
    pfn_vkCreateDisplayPlaneSurfaceKHR = (PFN_vkCreateDisplayPlaneSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateDisplayPlaneSurfaceKHR");
#endif /* VK_KHR_display */
#ifdef VK_KHR_display_swapchain
    pfn_vkCreateSharedSwapchainsKHR = (PFN_vkCreateSharedSwapchainsKHR)vkGetInstanceProcAddr(instance, "vkCreateSharedSwapchainsKHR");
#endif /* VK_KHR_display_swapchain */
#ifdef VK_KHR_xlib_surface
#ifndef VK_KHR_xlib_surface
    pfn_vkCreateXlibSurfaceKHR = (PFN_vkCreateXlibSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateXlibSurfaceKHR");
    pfn_vkGetPhysicalDeviceXlibPresentationSupportKHR = (PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceXlibPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_XLIB_KHR */
#endif /* VK_KHR_xlib_surface */
#ifdef VK_KHR_xcb_surface
#ifndef VK_KHR_xcb_surface
    pfn_vkCreateXcbSurfaceKHR = (PFN_vkCreateXcbSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateXcbSurfaceKHR");
    pfn_vkGetPhysicalDeviceXcbPresentationSupportKHR = (PFN_vkGetPhysicalDeviceXcbPresentationSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceXcbPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_XCB_KHR */
#endif /* VK_KHR_xcb_surface */
#ifdef VK_KHR_wayland_surface
#ifndef VK_KHR_wayland_surface
    pfn_vkCreateWaylandSurfaceKHR = (PFN_vkCreateWaylandSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateWaylandSurfaceKHR");
    pfn_vkGetPhysicalDeviceWaylandPresentationSupportKHR = (PFN_vkGetPhysicalDeviceWaylandPresentationSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceWaylandPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_WAYLAND_KHR */
#endif /* VK_KHR_wayland_surface */
#ifdef VK_KHR_mir_surface
#ifndef VK_KHR_mir_surface
    pfn_vkCreateMirSurfaceKHR = (PFN_vkCreateMirSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateMirSurfaceKHR");
    pfn_vkGetPhysicalDeviceMirPresentationSupportKHR = (PFN_vkGetPhysicalDeviceMirPresentationSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceMirPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_MIR_KHR */
#endif /* VK_KHR_mir_surface */
#ifdef VK_KHR_android_surface
#ifndef VK_KHR_android_surface
    pfn_vkCreateAndroidSurfaceKHR = (PFN_vkCreateAndroidSurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateAndroidSurfaceKHR");
#endif /* VK_USE_PLATFORM_ANDROID_KHR */
#endif /* VK_KHR_android_surface */
#ifdef VK_KHR_win32_surface
#ifndef VK_KHR_win32_surface
    pfn_vkCreateWin32SurfaceKHR = (PFN_vkCreateWin32SurfaceKHR)vkGetInstanceProcAddr(instance, "vkCreateWin32SurfaceKHR");
    pfn_vkGetPhysicalDeviceWin32PresentationSupportKHR = (PFN_vkGetPhysicalDeviceWin32PresentationSupportKHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceWin32PresentationSupportKHR");
#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_KHR_win32_surface */
#ifdef VK_EXT_debug_report
    pfn_vkCreateDebugReportCallbackEXT = (PFN_vkCreateDebugReportCallbackEXT)vkGetInstanceProcAddr(instance, "vkCreateDebugReportCallbackEXT");
    pfn_vkDestroyDebugReportCallbackEXT = (PFN_vkDestroyDebugReportCallbackEXT)vkGetInstanceProcAddr(instance, "vkDestroyDebugReportCallbackEXT");
    pfn_vkDebugReportMessageEXT = (PFN_vkDebugReportMessageEXT)vkGetInstanceProcAddr(instance, "vkDebugReportMessageEXT");
#endif /* VK_EXT_debug_report */
#ifdef VK_EXT_debug_marker
    pfn_vkDebugMarkerSetObjectTagEXT = (PFN_vkDebugMarkerSetObjectTagEXT)vkGetInstanceProcAddr(instance, "vkDebugMarkerSetObjectTagEXT");
    pfn_vkDebugMarkerSetObjectNameEXT = (PFN_vkDebugMarkerSetObjectNameEXT)vkGetInstanceProcAddr(instance, "vkDebugMarkerSetObjectNameEXT");
    pfn_vkCmdDebugMarkerBeginEXT = (PFN_vkCmdDebugMarkerBeginEXT)vkGetInstanceProcAddr(instance, "vkCmdDebugMarkerBeginEXT");
    pfn_vkCmdDebugMarkerEndEXT = (PFN_vkCmdDebugMarkerEndEXT)vkGetInstanceProcAddr(instance, "vkCmdDebugMarkerEndEXT");
    pfn_vkCmdDebugMarkerInsertEXT = (PFN_vkCmdDebugMarkerInsertEXT)vkGetInstanceProcAddr(instance, "vkCmdDebugMarkerInsertEXT");
#endif /* VK_EXT_debug_marker */
#ifdef VK_AMD_draw_indirect_count
    pfn_vkCmdDrawIndirectCountAMD = (PFN_vkCmdDrawIndirectCountAMD)vkGetInstanceProcAddr(instance, "vkCmdDrawIndirectCountAMD");
    pfn_vkCmdDrawIndexedIndirectCountAMD = (PFN_vkCmdDrawIndexedIndirectCountAMD)vkGetInstanceProcAddr(instance, "vkCmdDrawIndexedIndirectCountAMD");
#endif /* VK_AMD_draw_indirect_count */
#ifdef VK_NV_external_memory_capabilities
    pfn_vkGetPhysicalDeviceExternalImageFormatPropertiesNV = (PFN_vkGetPhysicalDeviceExternalImageFormatPropertiesNV)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceExternalImageFormatPropertiesNV");
#endif /* VK_NV_external_memory_capabilities */
#ifdef VK_NV_external_memory_win32
#ifndef VK_NV_external_memory_win32
    pfn_vkGetMemoryWin32HandleNV = (PFN_vkGetMemoryWin32HandleNV)vkGetInstanceProcAddr(instance, "vkGetMemoryWin32HandleNV");
#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_NV_external_memory_win32 */
}

void vkExtInitDevice(VkDevice device)
{
#ifdef VK_KHR_surface
    pfn_vkDestroySurfaceKHR = (PFN_vkDestroySurfaceKHR)vkGetDeviceProcAddr(device, "vkDestroySurfaceKHR");
    pfn_vkGetPhysicalDeviceSurfaceSupportKHR = (PFN_vkGetPhysicalDeviceSurfaceSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSurfaceSupportKHR");
    pfn_vkGetPhysicalDeviceSurfaceCapabilitiesKHR = (PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
    pfn_vkGetPhysicalDeviceSurfaceFormatsKHR = (PFN_vkGetPhysicalDeviceSurfaceFormatsKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSurfaceFormatsKHR");
    pfn_vkGetPhysicalDeviceSurfacePresentModesKHR = (PFN_vkGetPhysicalDeviceSurfacePresentModesKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSurfacePresentModesKHR");
#endif /* VK_KHR_surface */
#ifdef VK_KHR_swapchain
    pfn_vkCreateSwapchainKHR = (PFN_vkCreateSwapchainKHR)vkGetDeviceProcAddr(device, "vkCreateSwapchainKHR");
    pfn_vkDestroySwapchainKHR = (PFN_vkDestroySwapchainKHR)vkGetDeviceProcAddr(device, "vkDestroySwapchainKHR");
    pfn_vkGetSwapchainImagesKHR = (PFN_vkGetSwapchainImagesKHR)vkGetDeviceProcAddr(device, "vkGetSwapchainImagesKHR");
    pfn_vkAcquireNextImageKHR = (PFN_vkAcquireNextImageKHR)vkGetDeviceProcAddr(device, "vkAcquireNextImageKHR");
    pfn_vkQueuePresentKHR = (PFN_vkQueuePresentKHR)vkGetDeviceProcAddr(device, "vkQueuePresentKHR");
#endif /* VK_KHR_swapchain */
#ifdef VK_KHR_display
    pfn_vkGetPhysicalDeviceDisplayPropertiesKHR = (PFN_vkGetPhysicalDeviceDisplayPropertiesKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceDisplayPropertiesKHR");
    pfn_vkGetPhysicalDeviceDisplayPlanePropertiesKHR = (PFN_vkGetPhysicalDeviceDisplayPlanePropertiesKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceDisplayPlanePropertiesKHR");
    pfn_vkGetDisplayPlaneSupportedDisplaysKHR = (PFN_vkGetDisplayPlaneSupportedDisplaysKHR)vkGetDeviceProcAddr(device, "vkGetDisplayPlaneSupportedDisplaysKHR");
    pfn_vkGetDisplayModePropertiesKHR = (PFN_vkGetDisplayModePropertiesKHR)vkGetDeviceProcAddr(device, "vkGetDisplayModePropertiesKHR");
    pfn_vkCreateDisplayModeKHR = (PFN_vkCreateDisplayModeKHR)vkGetDeviceProcAddr(device, "vkCreateDisplayModeKHR");
    pfn_vkGetDisplayPlaneCapabilitiesKHR = (PFN_vkGetDisplayPlaneCapabilitiesKHR)vkGetDeviceProcAddr(device, "vkGetDisplayPlaneCapabilitiesKHR");
    pfn_vkCreateDisplayPlaneSurfaceKHR = (PFN_vkCreateDisplayPlaneSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateDisplayPlaneSurfaceKHR");
#endif /* VK_KHR_display */
#ifdef VK_KHR_display_swapchain
    pfn_vkCreateSharedSwapchainsKHR = (PFN_vkCreateSharedSwapchainsKHR)vkGetDeviceProcAddr(device, "vkCreateSharedSwapchainsKHR");
#endif /* VK_KHR_display_swapchain */
#ifdef VK_KHR_xlib_surface
#ifndef VK_KHR_xlib_surface
    pfn_vkCreateXlibSurfaceKHR = (PFN_vkCreateXlibSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateXlibSurfaceKHR");
    pfn_vkGetPhysicalDeviceXlibPresentationSupportKHR = (PFN_vkGetPhysicalDeviceXlibPresentationSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceXlibPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_XLIB_KHR */
#endif /* VK_KHR_xlib_surface */
#ifdef VK_KHR_xcb_surface
#ifndef VK_KHR_xcb_surface
    pfn_vkCreateXcbSurfaceKHR = (PFN_vkCreateXcbSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateXcbSurfaceKHR");
    pfn_vkGetPhysicalDeviceXcbPresentationSupportKHR = (PFN_vkGetPhysicalDeviceXcbPresentationSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceXcbPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_XCB_KHR */
#endif /* VK_KHR_xcb_surface */
#ifdef VK_KHR_wayland_surface
#ifndef VK_KHR_wayland_surface
    pfn_vkCreateWaylandSurfaceKHR = (PFN_vkCreateWaylandSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateWaylandSurfaceKHR");
    pfn_vkGetPhysicalDeviceWaylandPresentationSupportKHR = (PFN_vkGetPhysicalDeviceWaylandPresentationSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceWaylandPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_WAYLAND_KHR */
#endif /* VK_KHR_wayland_surface */
#ifdef VK_KHR_mir_surface
#ifndef VK_KHR_mir_surface
    pfn_vkCreateMirSurfaceKHR = (PFN_vkCreateMirSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateMirSurfaceKHR");
    pfn_vkGetPhysicalDeviceMirPresentationSupportKHR = (PFN_vkGetPhysicalDeviceMirPresentationSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceMirPresentationSupportKHR");
#endif /* VK_USE_PLATFORM_MIR_KHR */
#endif /* VK_KHR_mir_surface */
#ifdef VK_KHR_android_surface
#ifndef VK_KHR_android_surface
    pfn_vkCreateAndroidSurfaceKHR = (PFN_vkCreateAndroidSurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateAndroidSurfaceKHR");
#endif /* VK_USE_PLATFORM_ANDROID_KHR */
#endif /* VK_KHR_android_surface */
#ifdef VK_KHR_win32_surface
#ifndef VK_KHR_win32_surface
    pfn_vkCreateWin32SurfaceKHR = (PFN_vkCreateWin32SurfaceKHR)vkGetDeviceProcAddr(device, "vkCreateWin32SurfaceKHR");
    pfn_vkGetPhysicalDeviceWin32PresentationSupportKHR = (PFN_vkGetPhysicalDeviceWin32PresentationSupportKHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceWin32PresentationSupportKHR");
#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_KHR_win32_surface */
#ifdef VK_EXT_debug_report
    pfn_vkCreateDebugReportCallbackEXT = (PFN_vkCreateDebugReportCallbackEXT)vkGetDeviceProcAddr(device, "vkCreateDebugReportCallbackEXT");
    pfn_vkDestroyDebugReportCallbackEXT = (PFN_vkDestroyDebugReportCallbackEXT)vkGetDeviceProcAddr(device, "vkDestroyDebugReportCallbackEXT");
    pfn_vkDebugReportMessageEXT = (PFN_vkDebugReportMessageEXT)vkGetDeviceProcAddr(device, "vkDebugReportMessageEXT");
#endif /* VK_EXT_debug_report */
#ifdef VK_EXT_debug_marker
    pfn_vkDebugMarkerSetObjectTagEXT = (PFN_vkDebugMarkerSetObjectTagEXT)vkGetDeviceProcAddr(device, "vkDebugMarkerSetObjectTagEXT");
    pfn_vkDebugMarkerSetObjectNameEXT = (PFN_vkDebugMarkerSetObjectNameEXT)vkGetDeviceProcAddr(device, "vkDebugMarkerSetObjectNameEXT");
    pfn_vkCmdDebugMarkerBeginEXT = (PFN_vkCmdDebugMarkerBeginEXT)vkGetDeviceProcAddr(device, "vkCmdDebugMarkerBeginEXT");
    pfn_vkCmdDebugMarkerEndEXT = (PFN_vkCmdDebugMarkerEndEXT)vkGetDeviceProcAddr(device, "vkCmdDebugMarkerEndEXT");
    pfn_vkCmdDebugMarkerInsertEXT = (PFN_vkCmdDebugMarkerInsertEXT)vkGetDeviceProcAddr(device, "vkCmdDebugMarkerInsertEXT");
#endif /* VK_EXT_debug_marker */
#ifdef VK_AMD_draw_indirect_count
    pfn_vkCmdDrawIndirectCountAMD = (PFN_vkCmdDrawIndirectCountAMD)vkGetDeviceProcAddr(device, "vkCmdDrawIndirectCountAMD");
    pfn_vkCmdDrawIndexedIndirectCountAMD = (PFN_vkCmdDrawIndexedIndirectCountAMD)vkGetDeviceProcAddr(device, "vkCmdDrawIndexedIndirectCountAMD");
#endif /* VK_AMD_draw_indirect_count */
#ifdef VK_NV_external_memory_capabilities
    pfn_vkGetPhysicalDeviceExternalImageFormatPropertiesNV = (PFN_vkGetPhysicalDeviceExternalImageFormatPropertiesNV)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceExternalImageFormatPropertiesNV");
#endif /* VK_NV_external_memory_capabilities */
#ifdef VK_NV_external_memory_win32
#ifndef VK_NV_external_memory_win32
    pfn_vkGetMemoryWin32HandleNV = (PFN_vkGetMemoryWin32HandleNV)vkGetDeviceProcAddr(device, "vkGetMemoryWin32HandleNV");
#endif /* VK_USE_PLATFORM_WIN32_KHR */
#endif /* VK_NV_external_memory_win32 */
}

