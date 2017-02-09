/*
** Copyright (c) 2015-2017 The Khronos Group Inc.
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
VKAPI_ATTR void VKAPI_CALL vkDestroySurfaceKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceSupportKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceFormatsKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfacePresentModesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateSwapchainKHR(
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
VKAPI_ATTR void VKAPI_CALL vkDestroySwapchainKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetSwapchainImagesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkAcquireNextImageKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkQueuePresentKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceDisplayPropertiesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceDisplayPlanePropertiesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetDisplayPlaneSupportedDisplaysKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetDisplayModePropertiesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateDisplayModeKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetDisplayPlaneCapabilitiesKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateDisplayPlaneSurfaceKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateSharedSwapchainsKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateXlibSurfaceKHR(
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
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceXlibPresentationSupportKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateXcbSurfaceKHR(
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
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceXcbPresentationSupportKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateWaylandSurfaceKHR(
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
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceWaylandPresentationSupportKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateMirSurfaceKHR(
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
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceMirPresentationSupportKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateAndroidSurfaceKHR(
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
VKAPI_ATTR VkResult VKAPI_CALL vkCreateWin32SurfaceKHR(
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
VKAPI_ATTR VkBool32 VKAPI_CALL vkGetPhysicalDeviceWin32PresentationSupportKHR(
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
#ifdef VK_KHR_get_physical_device_properties2
static PFN_vkGetPhysicalDeviceFeatures2KHR pfn_vkGetPhysicalDeviceFeatures2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceFeatures2KHR(
    VkPhysicalDevice                            physicalDevice,
    VkPhysicalDeviceFeatures2KHR*               pFeatures)
{
    pfn_vkGetPhysicalDeviceFeatures2KHR(
        physicalDevice,
        pFeatures
    );
}

static PFN_vkGetPhysicalDeviceProperties2KHR pfn_vkGetPhysicalDeviceProperties2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    VkPhysicalDeviceProperties2KHR*             pProperties)
{
    pfn_vkGetPhysicalDeviceProperties2KHR(
        physicalDevice,
        pProperties
    );
}

static PFN_vkGetPhysicalDeviceFormatProperties2KHR pfn_vkGetPhysicalDeviceFormatProperties2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceFormatProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    VkFormat                                    format,
    VkFormatProperties2KHR*                     pFormatProperties)
{
    pfn_vkGetPhysicalDeviceFormatProperties2KHR(
        physicalDevice,
        format,
        pFormatProperties
    );
}

static PFN_vkGetPhysicalDeviceImageFormatProperties2KHR pfn_vkGetPhysicalDeviceImageFormatProperties2KHR;
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceImageFormatProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    const VkPhysicalDeviceImageFormatInfo2KHR*  pImageFormatInfo,
    VkImageFormatProperties2KHR*                pImageFormatProperties)
{
    return pfn_vkGetPhysicalDeviceImageFormatProperties2KHR(
        physicalDevice,
        pImageFormatInfo,
        pImageFormatProperties
    );
}

static PFN_vkGetPhysicalDeviceQueueFamilyProperties2KHR pfn_vkGetPhysicalDeviceQueueFamilyProperties2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceQueueFamilyProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    uint32_t*                                   pQueueFamilyPropertyCount,
    VkQueueFamilyProperties2KHR*                pQueueFamilyProperties)
{
    pfn_vkGetPhysicalDeviceQueueFamilyProperties2KHR(
        physicalDevice,
        pQueueFamilyPropertyCount,
        pQueueFamilyProperties
    );
}

static PFN_vkGetPhysicalDeviceMemoryProperties2KHR pfn_vkGetPhysicalDeviceMemoryProperties2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceMemoryProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    VkPhysicalDeviceMemoryProperties2KHR*       pMemoryProperties)
{
    pfn_vkGetPhysicalDeviceMemoryProperties2KHR(
        physicalDevice,
        pMemoryProperties
    );
}

static PFN_vkGetPhysicalDeviceSparseImageFormatProperties2KHR pfn_vkGetPhysicalDeviceSparseImageFormatProperties2KHR;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceSparseImageFormatProperties2KHR(
    VkPhysicalDevice                            physicalDevice,
    const VkPhysicalDeviceSparseImageFormatInfo2KHR* pFormatInfo,
    uint32_t*                                   pPropertyCount,
    VkSparseImageFormatProperties2KHR*          pProperties)
{
    pfn_vkGetPhysicalDeviceSparseImageFormatProperties2KHR(
        physicalDevice,
        pFormatInfo,
        pPropertyCount,
        pProperties
    );
}

#endif /* VK_KHR_get_physical_device_properties2 */
#ifdef VK_KHR_maintenance1
static PFN_vkTrimCommandPoolKHR pfn_vkTrimCommandPoolKHR;
VKAPI_ATTR void VKAPI_CALL vkTrimCommandPoolKHR(
    VkDevice                                    device,
    VkCommandPool                               commandPool,
    VkCommandPoolTrimFlagsKHR                   flags)
{
    pfn_vkTrimCommandPoolKHR(
        device,
        commandPool,
        flags
    );
}

#endif /* VK_KHR_maintenance1 */
#ifdef VK_EXT_debug_report
static PFN_vkCreateDebugReportCallbackEXT pfn_vkCreateDebugReportCallbackEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkCreateDebugReportCallbackEXT(
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
VKAPI_ATTR void VKAPI_CALL vkDestroyDebugReportCallbackEXT(
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
VKAPI_ATTR void VKAPI_CALL vkDebugReportMessageEXT(
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
VKAPI_ATTR VkResult VKAPI_CALL vkDebugMarkerSetObjectTagEXT(
    VkDevice                                    device,
    VkDebugMarkerObjectTagInfoEXT*              pTagInfo)
{
    return pfn_vkDebugMarkerSetObjectTagEXT(
        device,
        pTagInfo
    );
}

static PFN_vkDebugMarkerSetObjectNameEXT pfn_vkDebugMarkerSetObjectNameEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkDebugMarkerSetObjectNameEXT(
    VkDevice                                    device,
    VkDebugMarkerObjectNameInfoEXT*             pNameInfo)
{
    return pfn_vkDebugMarkerSetObjectNameEXT(
        device,
        pNameInfo
    );
}

static PFN_vkCmdDebugMarkerBeginEXT pfn_vkCmdDebugMarkerBeginEXT;
VKAPI_ATTR void VKAPI_CALL vkCmdDebugMarkerBeginEXT(
    VkCommandBuffer                             commandBuffer,
    VkDebugMarkerMarkerInfoEXT*                 pMarkerInfo)
{
    pfn_vkCmdDebugMarkerBeginEXT(
        commandBuffer,
        pMarkerInfo
    );
}

static PFN_vkCmdDebugMarkerEndEXT pfn_vkCmdDebugMarkerEndEXT;
VKAPI_ATTR void VKAPI_CALL vkCmdDebugMarkerEndEXT(
    VkCommandBuffer                             commandBuffer)
{
    pfn_vkCmdDebugMarkerEndEXT(
        commandBuffer
    );
}

static PFN_vkCmdDebugMarkerInsertEXT pfn_vkCmdDebugMarkerInsertEXT;
VKAPI_ATTR void VKAPI_CALL vkCmdDebugMarkerInsertEXT(
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
VKAPI_ATTR void VKAPI_CALL vkCmdDrawIndirectCountAMD(
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
VKAPI_ATTR void VKAPI_CALL vkCmdDrawIndexedIndirectCountAMD(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceExternalImageFormatPropertiesNV(
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
VKAPI_ATTR VkResult VKAPI_CALL vkGetMemoryWin32HandleNV(
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
#ifdef VK_NN_vi_surface
#ifdef VK_USE_PLATFORM_VI_NN
static PFN_vkCreateViSurfaceNN pfn_vkCreateViSurfaceNN;
VKAPI_ATTR VkResult VKAPI_CALL vkCreateViSurfaceNN(
    VkInstance                                  instance,
    const VkViSurfaceCreateInfoNN*              pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkSurfaceKHR*                               pSurface)
{
    return pfn_vkCreateViSurfaceNN(
        instance,
        pCreateInfo,
        pAllocator,
        pSurface
    );
}

#endif /* VK_USE_PLATFORM_VI_NN */
#endif /* VK_NN_vi_surface */
#ifdef VK_NVX_device_generated_commands
static PFN_vkCmdProcessCommandsNVX pfn_vkCmdProcessCommandsNVX;
VKAPI_ATTR void VKAPI_CALL vkCmdProcessCommandsNVX(
    VkCommandBuffer                             commandBuffer,
    const VkCmdProcessCommandsInfoNVX*          pProcessCommandsInfo)
{
    pfn_vkCmdProcessCommandsNVX(
        commandBuffer,
        pProcessCommandsInfo
    );
}

static PFN_vkCmdReserveSpaceForCommandsNVX pfn_vkCmdReserveSpaceForCommandsNVX;
VKAPI_ATTR void VKAPI_CALL vkCmdReserveSpaceForCommandsNVX(
    VkCommandBuffer                             commandBuffer,
    const VkCmdReserveSpaceForCommandsInfoNVX*  pReserveSpaceInfo)
{
    pfn_vkCmdReserveSpaceForCommandsNVX(
        commandBuffer,
        pReserveSpaceInfo
    );
}

static PFN_vkCreateIndirectCommandsLayoutNVX pfn_vkCreateIndirectCommandsLayoutNVX;
VKAPI_ATTR VkResult VKAPI_CALL vkCreateIndirectCommandsLayoutNVX(
    VkDevice                                    device,
    const VkIndirectCommandsLayoutCreateInfoNVX* pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkIndirectCommandsLayoutNVX*                pIndirectCommandsLayout)
{
    return pfn_vkCreateIndirectCommandsLayoutNVX(
        device,
        pCreateInfo,
        pAllocator,
        pIndirectCommandsLayout
    );
}

static PFN_vkDestroyIndirectCommandsLayoutNVX pfn_vkDestroyIndirectCommandsLayoutNVX;
VKAPI_ATTR void VKAPI_CALL vkDestroyIndirectCommandsLayoutNVX(
    VkDevice                                    device,
    VkIndirectCommandsLayoutNVX                 indirectCommandsLayout,
    const VkAllocationCallbacks*                pAllocator)
{
    pfn_vkDestroyIndirectCommandsLayoutNVX(
        device,
        indirectCommandsLayout,
        pAllocator
    );
}

static PFN_vkCreateObjectTableNVX pfn_vkCreateObjectTableNVX;
VKAPI_ATTR VkResult VKAPI_CALL vkCreateObjectTableNVX(
    VkDevice                                    device,
    const VkObjectTableCreateInfoNVX*           pCreateInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkObjectTableNVX*                           pObjectTable)
{
    return pfn_vkCreateObjectTableNVX(
        device,
        pCreateInfo,
        pAllocator,
        pObjectTable
    );
}

static PFN_vkDestroyObjectTableNVX pfn_vkDestroyObjectTableNVX;
VKAPI_ATTR void VKAPI_CALL vkDestroyObjectTableNVX(
    VkDevice                                    device,
    VkObjectTableNVX                            objectTable,
    const VkAllocationCallbacks*                pAllocator)
{
    pfn_vkDestroyObjectTableNVX(
        device,
        objectTable,
        pAllocator
    );
}

static PFN_vkRegisterObjectsNVX pfn_vkRegisterObjectsNVX;
VKAPI_ATTR VkResult VKAPI_CALL vkRegisterObjectsNVX(
    VkDevice                                    device,
    VkObjectTableNVX                            objectTable,
    uint32_t                                    objectCount,
    const VkObjectTableEntryNVX* const*         ppObjectTableEntries,
    const uint32_t*                             pObjectIndices)
{
    return pfn_vkRegisterObjectsNVX(
        device,
        objectTable,
        objectCount,
        ppObjectTableEntries,
        pObjectIndices
    );
}

static PFN_vkUnregisterObjectsNVX pfn_vkUnregisterObjectsNVX;
VKAPI_ATTR VkResult VKAPI_CALL vkUnregisterObjectsNVX(
    VkDevice                                    device,
    VkObjectTableNVX                            objectTable,
    uint32_t                                    objectCount,
    const VkObjectEntryTypeNVX*                 pObjectEntryTypes,
    const uint32_t*                             pObjectIndices)
{
    return pfn_vkUnregisterObjectsNVX(
        device,
        objectTable,
        objectCount,
        pObjectEntryTypes,
        pObjectIndices
    );
}

static PFN_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX pfn_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX;
VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX(
    VkPhysicalDevice                            physicalDevice,
    VkDeviceGeneratedCommandsFeaturesNVX*       pFeatures,
    VkDeviceGeneratedCommandsLimitsNVX*         pLimits)
{
    pfn_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX(
        physicalDevice,
        pFeatures,
        pLimits
    );
}

#endif /* VK_NVX_device_generated_commands */
#ifdef VK_EXT_direct_mode_display
static PFN_vkReleaseDisplayEXT pfn_vkReleaseDisplayEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkReleaseDisplayEXT(
    VkPhysicalDevice                            physicalDevice,
    VkDisplayKHR                                display)
{
    return pfn_vkReleaseDisplayEXT(
        physicalDevice,
        display
    );
}

#endif /* VK_EXT_direct_mode_display */
#ifdef VK_EXT_acquire_xlib_display
#ifdef VK_USE_PLATFORM_XLIB_XRANDR_EXT
static PFN_vkAcquireXlibDisplayEXT pfn_vkAcquireXlibDisplayEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkAcquireXlibDisplayEXT(
    VkPhysicalDevice                            physicalDevice,
    Display*                                    dpy,
    VkDisplayKHR                                display)
{
    return pfn_vkAcquireXlibDisplayEXT(
        physicalDevice,
        dpy,
        display
    );
}

static PFN_vkGetRandROutputDisplayEXT pfn_vkGetRandROutputDisplayEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkGetRandROutputDisplayEXT(
    VkPhysicalDevice                            physicalDevice,
    Display*                                    dpy,
    RROutput                                    rrOutput,
    VkDisplayKHR*                               pDisplay)
{
    return pfn_vkGetRandROutputDisplayEXT(
        physicalDevice,
        dpy,
        rrOutput,
        pDisplay
    );
}

#endif /* VK_USE_PLATFORM_XLIB_XRANDR_EXT */
#endif /* VK_EXT_acquire_xlib_display */
#ifdef VK_EXT_display_surface_counter
static PFN_vkGetPhysicalDeviceSurfaceCapabilities2EXT pfn_vkGetPhysicalDeviceSurfaceCapabilities2EXT;
VKAPI_ATTR VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceCapabilities2EXT(
    VkPhysicalDevice                            physicalDevice,
    VkSurfaceKHR                                surface,
    VkSurfaceCapabilities2EXT*                  pSurfaceCapabilities)
{
    return pfn_vkGetPhysicalDeviceSurfaceCapabilities2EXT(
        physicalDevice,
        surface,
        pSurfaceCapabilities
    );
}

#endif /* VK_EXT_display_surface_counter */
#ifdef VK_EXT_display_control
static PFN_vkDisplayPowerControlEXT pfn_vkDisplayPowerControlEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkDisplayPowerControlEXT(
    VkDevice                                    device,
    VkDisplayKHR                                display,
    const VkDisplayPowerInfoEXT*                pDisplayPowerInfo)
{
    return pfn_vkDisplayPowerControlEXT(
        device,
        display,
        pDisplayPowerInfo
    );
}

static PFN_vkRegisterDeviceEventEXT pfn_vkRegisterDeviceEventEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkRegisterDeviceEventEXT(
    VkDevice                                    device,
    const VkDeviceEventInfoEXT*                 pDeviceEventInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkFence*                                    pFence)
{
    return pfn_vkRegisterDeviceEventEXT(
        device,
        pDeviceEventInfo,
        pAllocator,
        pFence
    );
}

static PFN_vkRegisterDisplayEventEXT pfn_vkRegisterDisplayEventEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkRegisterDisplayEventEXT(
    VkDevice                                    device,
    VkDisplayKHR                                display,
    const VkDisplayEventInfoEXT*                pDisplayEventInfo,
    const VkAllocationCallbacks*                pAllocator,
    VkFence*                                    pFence)
{
    return pfn_vkRegisterDisplayEventEXT(
        device,
        display,
        pDisplayEventInfo,
        pAllocator,
        pFence
    );
}

static PFN_vkGetSwapchainCounterEXT pfn_vkGetSwapchainCounterEXT;
VKAPI_ATTR VkResult VKAPI_CALL vkGetSwapchainCounterEXT(
    VkDevice                                    device,
    VkSwapchainKHR                              swapchain,
    VkSurfaceCounterFlagBitsEXT                 counter,
    uint64_t*                                   pCounterValue)
{
    return pfn_vkGetSwapchainCounterEXT(
        device,
        swapchain,
        counter,
        pCounterValue
    );
}

#endif /* VK_EXT_display_control */

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
#ifdef VK_KHR_get_physical_device_properties2
    pfn_vkGetPhysicalDeviceFeatures2KHR = (PFN_vkGetPhysicalDeviceFeatures2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceFeatures2KHR");
    pfn_vkGetPhysicalDeviceProperties2KHR = (PFN_vkGetPhysicalDeviceProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceProperties2KHR");
    pfn_vkGetPhysicalDeviceFormatProperties2KHR = (PFN_vkGetPhysicalDeviceFormatProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceFormatProperties2KHR");
    pfn_vkGetPhysicalDeviceImageFormatProperties2KHR = (PFN_vkGetPhysicalDeviceImageFormatProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceImageFormatProperties2KHR");
    pfn_vkGetPhysicalDeviceQueueFamilyProperties2KHR = (PFN_vkGetPhysicalDeviceQueueFamilyProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceQueueFamilyProperties2KHR");
    pfn_vkGetPhysicalDeviceMemoryProperties2KHR = (PFN_vkGetPhysicalDeviceMemoryProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceMemoryProperties2KHR");
    pfn_vkGetPhysicalDeviceSparseImageFormatProperties2KHR = (PFN_vkGetPhysicalDeviceSparseImageFormatProperties2KHR)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSparseImageFormatProperties2KHR");
#endif /* VK_KHR_get_physical_device_properties2 */
#ifdef VK_KHR_maintenance1
    pfn_vkTrimCommandPoolKHR = (PFN_vkTrimCommandPoolKHR)vkGetInstanceProcAddr(instance, "vkTrimCommandPoolKHR");
#endif /* VK_KHR_maintenance1 */
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
#ifdef VK_NN_vi_surface
#ifndef VK_NN_vi_surface
    pfn_vkCreateViSurfaceNN = (PFN_vkCreateViSurfaceNN)vkGetInstanceProcAddr(instance, "vkCreateViSurfaceNN");
#endif /* VK_USE_PLATFORM_VI_NN */
#endif /* VK_NN_vi_surface */
#ifdef VK_NVX_device_generated_commands
    pfn_vkCmdProcessCommandsNVX = (PFN_vkCmdProcessCommandsNVX)vkGetInstanceProcAddr(instance, "vkCmdProcessCommandsNVX");
    pfn_vkCmdReserveSpaceForCommandsNVX = (PFN_vkCmdReserveSpaceForCommandsNVX)vkGetInstanceProcAddr(instance, "vkCmdReserveSpaceForCommandsNVX");
    pfn_vkCreateIndirectCommandsLayoutNVX = (PFN_vkCreateIndirectCommandsLayoutNVX)vkGetInstanceProcAddr(instance, "vkCreateIndirectCommandsLayoutNVX");
    pfn_vkDestroyIndirectCommandsLayoutNVX = (PFN_vkDestroyIndirectCommandsLayoutNVX)vkGetInstanceProcAddr(instance, "vkDestroyIndirectCommandsLayoutNVX");
    pfn_vkCreateObjectTableNVX = (PFN_vkCreateObjectTableNVX)vkGetInstanceProcAddr(instance, "vkCreateObjectTableNVX");
    pfn_vkDestroyObjectTableNVX = (PFN_vkDestroyObjectTableNVX)vkGetInstanceProcAddr(instance, "vkDestroyObjectTableNVX");
    pfn_vkRegisterObjectsNVX = (PFN_vkRegisterObjectsNVX)vkGetInstanceProcAddr(instance, "vkRegisterObjectsNVX");
    pfn_vkUnregisterObjectsNVX = (PFN_vkUnregisterObjectsNVX)vkGetInstanceProcAddr(instance, "vkUnregisterObjectsNVX");
    pfn_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX = (PFN_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX");
#endif /* VK_NVX_device_generated_commands */
#ifdef VK_EXT_direct_mode_display
    pfn_vkReleaseDisplayEXT = (PFN_vkReleaseDisplayEXT)vkGetInstanceProcAddr(instance, "vkReleaseDisplayEXT");
#endif /* VK_EXT_direct_mode_display */
#ifdef VK_EXT_acquire_xlib_display
#ifndef VK_EXT_acquire_xlib_display
    pfn_vkAcquireXlibDisplayEXT = (PFN_vkAcquireXlibDisplayEXT)vkGetInstanceProcAddr(instance, "vkAcquireXlibDisplayEXT");
    pfn_vkGetRandROutputDisplayEXT = (PFN_vkGetRandROutputDisplayEXT)vkGetInstanceProcAddr(instance, "vkGetRandROutputDisplayEXT");
#endif /* VK_USE_PLATFORM_XLIB_XRANDR_EXT */
#endif /* VK_EXT_acquire_xlib_display */
#ifdef VK_EXT_display_surface_counter
    pfn_vkGetPhysicalDeviceSurfaceCapabilities2EXT = (PFN_vkGetPhysicalDeviceSurfaceCapabilities2EXT)vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceCapabilities2EXT");
#endif /* VK_EXT_display_surface_counter */
#ifdef VK_EXT_display_control
    pfn_vkDisplayPowerControlEXT = (PFN_vkDisplayPowerControlEXT)vkGetInstanceProcAddr(instance, "vkDisplayPowerControlEXT");
    pfn_vkRegisterDeviceEventEXT = (PFN_vkRegisterDeviceEventEXT)vkGetInstanceProcAddr(instance, "vkRegisterDeviceEventEXT");
    pfn_vkRegisterDisplayEventEXT = (PFN_vkRegisterDisplayEventEXT)vkGetInstanceProcAddr(instance, "vkRegisterDisplayEventEXT");
    pfn_vkGetSwapchainCounterEXT = (PFN_vkGetSwapchainCounterEXT)vkGetInstanceProcAddr(instance, "vkGetSwapchainCounterEXT");
#endif /* VK_EXT_display_control */
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
#ifdef VK_KHR_get_physical_device_properties2
    pfn_vkGetPhysicalDeviceFeatures2KHR = (PFN_vkGetPhysicalDeviceFeatures2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceFeatures2KHR");
    pfn_vkGetPhysicalDeviceProperties2KHR = (PFN_vkGetPhysicalDeviceProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceProperties2KHR");
    pfn_vkGetPhysicalDeviceFormatProperties2KHR = (PFN_vkGetPhysicalDeviceFormatProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceFormatProperties2KHR");
    pfn_vkGetPhysicalDeviceImageFormatProperties2KHR = (PFN_vkGetPhysicalDeviceImageFormatProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceImageFormatProperties2KHR");
    pfn_vkGetPhysicalDeviceQueueFamilyProperties2KHR = (PFN_vkGetPhysicalDeviceQueueFamilyProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceQueueFamilyProperties2KHR");
    pfn_vkGetPhysicalDeviceMemoryProperties2KHR = (PFN_vkGetPhysicalDeviceMemoryProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceMemoryProperties2KHR");
    pfn_vkGetPhysicalDeviceSparseImageFormatProperties2KHR = (PFN_vkGetPhysicalDeviceSparseImageFormatProperties2KHR)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSparseImageFormatProperties2KHR");
#endif /* VK_KHR_get_physical_device_properties2 */
#ifdef VK_KHR_maintenance1
    pfn_vkTrimCommandPoolKHR = (PFN_vkTrimCommandPoolKHR)vkGetDeviceProcAddr(device, "vkTrimCommandPoolKHR");
#endif /* VK_KHR_maintenance1 */
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
#ifdef VK_NN_vi_surface
#ifndef VK_NN_vi_surface
    pfn_vkCreateViSurfaceNN = (PFN_vkCreateViSurfaceNN)vkGetDeviceProcAddr(device, "vkCreateViSurfaceNN");
#endif /* VK_USE_PLATFORM_VI_NN */
#endif /* VK_NN_vi_surface */
#ifdef VK_NVX_device_generated_commands
    pfn_vkCmdProcessCommandsNVX = (PFN_vkCmdProcessCommandsNVX)vkGetDeviceProcAddr(device, "vkCmdProcessCommandsNVX");
    pfn_vkCmdReserveSpaceForCommandsNVX = (PFN_vkCmdReserveSpaceForCommandsNVX)vkGetDeviceProcAddr(device, "vkCmdReserveSpaceForCommandsNVX");
    pfn_vkCreateIndirectCommandsLayoutNVX = (PFN_vkCreateIndirectCommandsLayoutNVX)vkGetDeviceProcAddr(device, "vkCreateIndirectCommandsLayoutNVX");
    pfn_vkDestroyIndirectCommandsLayoutNVX = (PFN_vkDestroyIndirectCommandsLayoutNVX)vkGetDeviceProcAddr(device, "vkDestroyIndirectCommandsLayoutNVX");
    pfn_vkCreateObjectTableNVX = (PFN_vkCreateObjectTableNVX)vkGetDeviceProcAddr(device, "vkCreateObjectTableNVX");
    pfn_vkDestroyObjectTableNVX = (PFN_vkDestroyObjectTableNVX)vkGetDeviceProcAddr(device, "vkDestroyObjectTableNVX");
    pfn_vkRegisterObjectsNVX = (PFN_vkRegisterObjectsNVX)vkGetDeviceProcAddr(device, "vkRegisterObjectsNVX");
    pfn_vkUnregisterObjectsNVX = (PFN_vkUnregisterObjectsNVX)vkGetDeviceProcAddr(device, "vkUnregisterObjectsNVX");
    pfn_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX = (PFN_vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceGeneratedCommandsPropertiesNVX");
#endif /* VK_NVX_device_generated_commands */
#ifdef VK_EXT_direct_mode_display
    pfn_vkReleaseDisplayEXT = (PFN_vkReleaseDisplayEXT)vkGetDeviceProcAddr(device, "vkReleaseDisplayEXT");
#endif /* VK_EXT_direct_mode_display */
#ifdef VK_EXT_acquire_xlib_display
#ifndef VK_EXT_acquire_xlib_display
    pfn_vkAcquireXlibDisplayEXT = (PFN_vkAcquireXlibDisplayEXT)vkGetDeviceProcAddr(device, "vkAcquireXlibDisplayEXT");
    pfn_vkGetRandROutputDisplayEXT = (PFN_vkGetRandROutputDisplayEXT)vkGetDeviceProcAddr(device, "vkGetRandROutputDisplayEXT");
#endif /* VK_USE_PLATFORM_XLIB_XRANDR_EXT */
#endif /* VK_EXT_acquire_xlib_display */
#ifdef VK_EXT_display_surface_counter
    pfn_vkGetPhysicalDeviceSurfaceCapabilities2EXT = (PFN_vkGetPhysicalDeviceSurfaceCapabilities2EXT)vkGetDeviceProcAddr(device, "vkGetPhysicalDeviceSurfaceCapabilities2EXT");
#endif /* VK_EXT_display_surface_counter */
#ifdef VK_EXT_display_control
    pfn_vkDisplayPowerControlEXT = (PFN_vkDisplayPowerControlEXT)vkGetDeviceProcAddr(device, "vkDisplayPowerControlEXT");
    pfn_vkRegisterDeviceEventEXT = (PFN_vkRegisterDeviceEventEXT)vkGetDeviceProcAddr(device, "vkRegisterDeviceEventEXT");
    pfn_vkRegisterDisplayEventEXT = (PFN_vkRegisterDisplayEventEXT)vkGetDeviceProcAddr(device, "vkRegisterDisplayEventEXT");
    pfn_vkGetSwapchainCounterEXT = (PFN_vkGetSwapchainCounterEXT)vkGetDeviceProcAddr(device, "vkGetSwapchainCounterEXT");
#endif /* VK_EXT_display_control */
}

