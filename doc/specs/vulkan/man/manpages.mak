MANDIR?=.
MANSECTION:=3

WSIFLAGSSOURCES=\
    $(MANDIR)/VkAndroidSurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkCompositeAlphaFlagsKHR.txt \
    $(MANDIR)/VkDisplayModeCreateFlagsKHR.txt \
    $(MANDIR)/VkDisplayPlaneAlphaFlagsKHR.txt \
    $(MANDIR)/VkDisplaySurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkMirSurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkSurfaceTransformFlagsKHR.txt \
    $(MANDIR)/VkSwapchainCreateFlagsKHR.txt \
    $(MANDIR)/VkWaylandSurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkWin32SurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkXcbSurfaceCreateFlagsKHR.txt \
    $(MANDIR)/VkXlibSurfaceCreateFlagsKHR.txt

WSISTRUCTSOURCES=\
    $(MANDIR)/VkAndroidSurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkDisplayModeCreateInfoKHR.txt \
    $(MANDIR)/VkDisplayModeParametersKHR.txt \
    $(MANDIR)/VkDisplayModePropertiesKHR.txt \
    $(MANDIR)/VkDisplayPlaneCapabilitiesKHR.txt \
    $(MANDIR)/VkDisplayPlanePropertiesKHR.txt \
    $(MANDIR)/VkDisplayPresentInfoKHR.txt \
    $(MANDIR)/VkDisplayPropertiesKHR.txt \
    $(MANDIR)/VkDisplaySurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkMirSurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkPresentInfoKHR.txt \
    $(MANDIR)/VkSurfaceCapabilitiesKHR.txt \
    $(MANDIR)/VkSurfaceFormatKHR.txt \
    $(MANDIR)/VkSwapchainCreateInfoKHR.txt \
    $(MANDIR)/VkWaylandSurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkWin32SurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkXcbSurfaceCreateInfoKHR.txt \
    $(MANDIR)/VkXlibSurfaceCreateInfoKHR.txt

WSIFUNCSOURCES=\
    $(MANDIR)/vkAcquireNextImageKHR.txt					       \
    $(MANDIR)/vkCreateAndroidSurfaceKHR.txt				       \
    $(MANDIR)/vkCreateDisplayModeKHR.txt				       \
    $(MANDIR)/vkCreateDisplayPlaneSurfaceKHR.txt			       \
    $(MANDIR)/vkCreateMirSurfaceKHR.txt					       \
    $(MANDIR)/vkCreateSharedSwapchainsKHR.txt				       \
    $(MANDIR)/vkCreateSwapchainKHR.txt					       \
    $(MANDIR)/vkCreateWaylandSurfaceKHR.txt				       \
    $(MANDIR)/vkCreateWin32SurfaceKHR.txt				       \
    $(MANDIR)/vkCreateXcbSurfaceKHR.txt					       \
    $(MANDIR)/vkCreateXlibSurfaceKHR.txt				       \
    $(MANDIR)/vkDestroySurfaceKHR.txt					       \
    $(MANDIR)/vkDestroySwapchainKHR.txt					       \
    $(MANDIR)/vkGetDisplayModePropertiesKHR.txt				       \
    $(MANDIR)/vkGetDisplayPlaneCapabilitiesKHR.txt			       \
    $(MANDIR)/vkGetDisplayPlaneSupportedDisplaysKHR.txt			       \
    $(MANDIR)/vkGetPhysicalDeviceDisplayPlanePropertiesKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceDisplayPropertiesKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceMirPresentationSupportKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceCapabilitiesKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceFormatsKHR.txt			       \
    $(MANDIR)/vkGetPhysicalDeviceSurfacePresentModesKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceSupportKHR.txt			       \
    $(MANDIR)/vkGetPhysicalDeviceWaylandPresentationSupportKHR.txt	       \
    $(MANDIR)/vkGetPhysicalDeviceWin32PresentationSupportKHR.txt	       \
    $(MANDIR)/vkGetPhysicalDeviceXcbPresentationSupportKHR.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceXlibPresentationSupportKHR.txt		       \
    $(MANDIR)/vkGetSwapchainImagesKHR.txt				       \
    $(MANDIR)/vkQueuePresentKHR.txt					       \

WSIENUMSOURCES=\
    $(MANDIR)/VkColorSpaceKHR.txt \
    $(MANDIR)/VkCompositeAlphaFlagBitsKHR.txt \
    $(MANDIR)/VkDisplayPlaneAlphaFlagBitsKHR.txt \
    $(MANDIR)/VkPresentModeKHR.txt \
    $(MANDIR)/VkSurfaceTransformFlagBitsKHR.txt

WSISOURCES = $(WSIENUMSOURCES) $(WSLFLAGSSOURCES) $(WSIFUNCSOURCES) $(WSISTRUCTSOURCES)

EXTSOURCES=\
    $(MANDIR)/VkDebugReportFlagsEXT.txt \
    $(MANDIR)/VkDebugReportErrorEXT.txt \
    $(MANDIR)/VkDebugReportFlagBitsEXT.txt \
    $(MANDIR)/VkDebugReportObjectTypeEXT.txt \
    $(MANDIR)/VkDebugReportCallbackCreateInfoEXT.txt \
    $(MANDIR)/vkCreateDebugReportCallbackEXT.txt \
    $(MANDIR)/vkDebugReportMessageEXT.txt \
    $(MANDIR)/vkDestroyDebugReportCallbackEXT.txt

FUNCSOURCES=\
    $(MANDIR)/vkAllocateCommandBuffers.txt				       \
    $(MANDIR)/vkAllocateDescriptorSets.txt				       \
    $(MANDIR)/vkAllocateMemory.txt					       \
    $(MANDIR)/vkBeginCommandBuffer.txt					       \
    $(MANDIR)/vkBindBufferMemory.txt					       \
    $(MANDIR)/vkBindImageMemory.txt					       \
    $(MANDIR)/vkCmdBeginQuery.txt					       \
    $(MANDIR)/vkCmdBeginRenderPass.txt					       \
    $(MANDIR)/vkCmdBindDescriptorSets.txt				       \
    $(MANDIR)/vkCmdBindIndexBuffer.txt					       \
    $(MANDIR)/vkCmdBindPipeline.txt					       \
    $(MANDIR)/vkCmdBindVertexBuffers.txt				       \
    $(MANDIR)/vkCmdBlitImage.txt					       \
    $(MANDIR)/vkCmdClearAttachments.txt					       \
    $(MANDIR)/vkCmdClearColorImage.txt					       \
    $(MANDIR)/vkCmdClearDepthStencilImage.txt				       \
    $(MANDIR)/vkCmdCopyBuffer.txt					       \
    $(MANDIR)/vkCmdCopyBufferToImage.txt				       \
    $(MANDIR)/vkCmdCopyImage.txt					       \
    $(MANDIR)/vkCmdCopyImageToBuffer.txt				       \
    $(MANDIR)/vkCmdCopyQueryPoolResults.txt				       \
    $(MANDIR)/vkCmdDispatch.txt						       \
    $(MANDIR)/vkCmdDispatchIndirect.txt					       \
    $(MANDIR)/vkCmdDraw.txt						       \
    $(MANDIR)/vkCmdDrawIndexed.txt					       \
    $(MANDIR)/vkCmdDrawIndexedIndirect.txt				       \
    $(MANDIR)/vkCmdDrawIndirect.txt					       \
    $(MANDIR)/vkCmdEndQuery.txt						       \
    $(MANDIR)/vkCmdEndRenderPass.txt					       \
    $(MANDIR)/vkCmdExecuteCommands.txt					       \
    $(MANDIR)/vkCmdFillBuffer.txt					       \
    $(MANDIR)/vkCmdNextSubpass.txt					       \
    $(MANDIR)/vkCmdPipelineBarrier.txt					       \
    $(MANDIR)/vkCmdPushConstants.txt					       \
    $(MANDIR)/vkCmdResetEvent.txt					       \
    $(MANDIR)/vkCmdResetQueryPool.txt					       \
    $(MANDIR)/vkCmdResolveImage.txt					       \
    $(MANDIR)/vkCmdSetBlendConstants.txt				       \
    $(MANDIR)/vkCmdSetDepthBias.txt					       \
    $(MANDIR)/vkCmdSetDepthBounds.txt					       \
    $(MANDIR)/vkCmdSetEvent.txt						       \
    $(MANDIR)/vkCmdSetLineWidth.txt					       \
    $(MANDIR)/vkCmdSetScissor.txt					       \
    $(MANDIR)/vkCmdSetStencilCompareMask.txt				       \
    $(MANDIR)/vkCmdSetStencilReference.txt				       \
    $(MANDIR)/vkCmdSetStencilWriteMask.txt				       \
    $(MANDIR)/vkCmdSetViewport.txt					       \
    $(MANDIR)/vkCmdUpdateBuffer.txt					       \
    $(MANDIR)/vkCmdWaitEvents.txt					       \
    $(MANDIR)/vkCmdWriteTimestamp.txt					       \
    $(MANDIR)/vkCreateBuffer.txt					       \
    $(MANDIR)/vkCreateBufferView.txt					       \
    $(MANDIR)/vkCreateCommandPool.txt					       \
    $(MANDIR)/vkCreateComputePipelines.txt				       \
    $(MANDIR)/vkCreateDescriptorPool.txt				       \
    $(MANDIR)/vkCreateDescriptorSetLayout.txt				       \
    $(MANDIR)/vkCreateDevice.txt					       \
    $(MANDIR)/vkCreateEvent.txt						       \
    $(MANDIR)/vkCreateFence.txt						       \
    $(MANDIR)/vkCreateFramebuffer.txt					       \
    $(MANDIR)/vkCreateGraphicsPipelines.txt				       \
    $(MANDIR)/vkCreateImage.txt						       \
    $(MANDIR)/vkCreateImageView.txt					       \
    $(MANDIR)/vkCreateInstance.txt					       \
    $(MANDIR)/vkCreatePipelineCache.txt					       \
    $(MANDIR)/vkCreatePipelineLayout.txt				       \
    $(MANDIR)/vkCreateQueryPool.txt					       \
    $(MANDIR)/vkCreateRenderPass.txt					       \
    $(MANDIR)/vkCreateSampler.txt					       \
    $(MANDIR)/vkCreateSemaphore.txt					       \
    $(MANDIR)/vkCreateShaderModule.txt					       \
    $(MANDIR)/vkDestroyBuffer.txt					       \
    $(MANDIR)/vkDestroyBufferView.txt					       \
    $(MANDIR)/vkDestroyCommandPool.txt					       \
    $(MANDIR)/vkDestroyDescriptorPool.txt				       \
    $(MANDIR)/vkDestroyDescriptorSetLayout.txt				       \
    $(MANDIR)/vkDestroyDevice.txt					       \
    $(MANDIR)/vkDestroyEvent.txt					       \
    $(MANDIR)/vkDestroyFence.txt					       \
    $(MANDIR)/vkDestroyFramebuffer.txt					       \
    $(MANDIR)/vkDestroyImage.txt					       \
    $(MANDIR)/vkDestroyImageView.txt					       \
    $(MANDIR)/vkDestroyInstance.txt					       \
    $(MANDIR)/vkDestroyPipeline.txt					       \
    $(MANDIR)/vkDestroyPipelineCache.txt				       \
    $(MANDIR)/vkDestroyPipelineLayout.txt				       \
    $(MANDIR)/vkDestroyQueryPool.txt					       \
    $(MANDIR)/vkDestroyRenderPass.txt					       \
    $(MANDIR)/vkDestroySampler.txt					       \
    $(MANDIR)/vkDestroySemaphore.txt					       \
    $(MANDIR)/vkDestroyShaderModule.txt					       \
    $(MANDIR)/vkDeviceWaitIdle.txt					       \
    $(MANDIR)/vkEndCommandBuffer.txt					       \
    $(MANDIR)/vkEnumerateDeviceExtensionProperties.txt			       \
    $(MANDIR)/vkEnumerateDeviceLayerProperties.txt			       \
    $(MANDIR)/vkEnumerateInstanceExtensionProperties.txt		       \
    $(MANDIR)/vkEnumerateInstanceLayerProperties.txt			       \
    $(MANDIR)/vkEnumeratePhysicalDevices.txt				       \
    $(MANDIR)/vkFlushMappedMemoryRanges.txt				       \
    $(MANDIR)/vkFreeCommandBuffers.txt					       \
    $(MANDIR)/vkFreeDescriptorSets.txt					       \
    $(MANDIR)/vkFreeMemory.txt						       \
    $(MANDIR)/vkGetBufferMemoryRequirements.txt				       \
    $(MANDIR)/vkGetDeviceMemoryCommitment.txt				       \
    $(MANDIR)/vkGetDeviceProcAddr.txt					       \
    $(MANDIR)/vkGetDeviceQueue.txt					       \
    $(MANDIR)/vkGetEventStatus.txt					       \
    $(MANDIR)/vkGetFenceStatus.txt					       \
    $(MANDIR)/vkGetImageMemoryRequirements.txt				       \
    $(MANDIR)/vkGetImageSparseMemoryRequirements.txt			       \
    $(MANDIR)/vkGetImageSubresourceLayout.txt				       \
    $(MANDIR)/vkGetInstanceProcAddr.txt					       \
    $(MANDIR)/vkGetPhysicalDeviceFeatures.txt				       \
    $(MANDIR)/vkGetPhysicalDeviceFormatProperties.txt			       \
    $(MANDIR)/vkGetPhysicalDeviceImageFormatProperties.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceMemoryProperties.txt			       \
    $(MANDIR)/vkGetPhysicalDeviceProperties.txt				       \
    $(MANDIR)/vkGetPhysicalDeviceQueueFamilyProperties.txt		       \
    $(MANDIR)/vkGetPhysicalDeviceSparseImageFormatProperties.txt	       \
    $(MANDIR)/vkGetPipelineCacheData.txt				       \
    $(MANDIR)/vkGetQueryPoolResults.txt					       \
    $(MANDIR)/vkGetRenderAreaGranularity.txt				       \
    $(MANDIR)/vkInvalidateMappedMemoryRanges.txt			       \
    $(MANDIR)/vkMapMemory.txt						       \
    $(MANDIR)/vkMergePipelineCaches.txt					       \
    $(MANDIR)/vkQueueBindSparse.txt					       \
    $(MANDIR)/vkQueueSubmit.txt						       \
    $(MANDIR)/vkQueueWaitIdle.txt					       \
    $(MANDIR)/vkResetCommandBuffer.txt					       \
    $(MANDIR)/vkResetCommandPool.txt					       \
    $(MANDIR)/vkResetDescriptorPool.txt					       \
    $(MANDIR)/vkResetEvent.txt						       \
    $(MANDIR)/vkResetFences.txt						       \
    $(MANDIR)/vkSetEvent.txt						       \
    $(MANDIR)/vkUnmapMemory.txt						       \
    $(MANDIR)/vkUpdateDescriptorSets.txt				       \
    $(MANDIR)/vkWaitForFences.txt

STRUCTSOURCES=\
    $(MANDIR)/VkAllocationCallbacks.txt \
    $(MANDIR)/VkCommandBufferAllocateInfo.txt \
    $(MANDIR)/VkDescriptorSetAllocateInfo.txt \
    $(MANDIR)/VkBufferCreateInfo.txt \
    $(MANDIR)/VkBufferMemoryBarrier.txt \
    $(MANDIR)/VkImageCreateInfo.txt \
    $(MANDIR)/VkImageMemoryBarrier.txt \
    $(MANDIR)/VkPhysicalDeviceFeatures.txt \
    $(MANDIR)/VkPhysicalDeviceLimits.txt \
    $(MANDIR)/VkPipelineLayoutCreateInfo.txt \
    $(MANDIR)/VkQueueFamilyProperties.txt \
    $(MANDIR)/VkWriteDescriptorSet.txt \
    $(MANDIR)/VkApplicationInfo.txt \
    $(MANDIR)/VkAttachmentDescription.txt \
    $(MANDIR)/VkAttachmentReference.txt \
    $(MANDIR)/VkBindSparseInfo.txt \
    $(MANDIR)/VkBufferCopy.txt \
    $(MANDIR)/VkBufferImageCopy.txt \
    $(MANDIR)/VkBufferViewCreateInfo.txt \
    $(MANDIR)/VkClearAttachment.txt \
    $(MANDIR)/VkClearColorValue.txt \
    $(MANDIR)/VkClearDepthStencilValue.txt \
    $(MANDIR)/VkClearRect.txt \
    $(MANDIR)/VkClearValue.txt \
    $(MANDIR)/VkCommandBufferBeginInfo.txt \
    $(MANDIR)/VkCommandBufferInheritanceInfo.txt \
    $(MANDIR)/VkCommandPoolCreateInfo.txt \
    $(MANDIR)/VkComponentMapping.txt \
    $(MANDIR)/VkComputePipelineCreateInfo.txt \
    $(MANDIR)/VkCopyDescriptorSet.txt \
    $(MANDIR)/VkDescriptorBufferInfo.txt \
    $(MANDIR)/VkDescriptorImageInfo.txt \
    $(MANDIR)/VkDescriptorPoolCreateInfo.txt \
    $(MANDIR)/VkDescriptorPoolSize.txt \
    $(MANDIR)/VkDescriptorSetLayoutBinding.txt \
    $(MANDIR)/VkDescriptorSetLayoutCreateInfo.txt \
    $(MANDIR)/VkDeviceCreateInfo.txt \
    $(MANDIR)/VkDeviceQueueCreateInfo.txt \
    $(MANDIR)/VkDispatchIndirectCommand.txt \
    $(MANDIR)/VkDrawIndexedIndirectCommand.txt \
    $(MANDIR)/VkDrawIndirectCommand.txt \
    $(MANDIR)/VkEventCreateInfo.txt \
    $(MANDIR)/VkExtensionProperties.txt \
    $(MANDIR)/VkExtent2D.txt \
    $(MANDIR)/VkExtent3D.txt \
    $(MANDIR)/VkFenceCreateInfo.txt \
    $(MANDIR)/VkFormatProperties.txt \
    $(MANDIR)/VkFramebufferCreateInfo.txt \
    $(MANDIR)/VkGraphicsPipelineCreateInfo.txt \
    $(MANDIR)/VkImageBlit.txt \
    $(MANDIR)/VkImageCopy.txt \
    $(MANDIR)/VkImageFormatProperties.txt \
    $(MANDIR)/VkImageResolve.txt \
    $(MANDIR)/VkImageSubresourceLayers.txt \
    $(MANDIR)/VkImageSubresourceRange.txt \
    $(MANDIR)/VkImageSubresource.txt \
    $(MANDIR)/VkImageViewCreateInfo.txt \
    $(MANDIR)/VkInstanceCreateInfo.txt \
    $(MANDIR)/VkLayerProperties.txt \
    $(MANDIR)/VkMappedMemoryRange.txt \
    $(MANDIR)/VkMemoryAllocateInfo.txt \
    $(MANDIR)/VkMemoryBarrier.txt \
    $(MANDIR)/VkMemoryHeap.txt \
    $(MANDIR)/VkMemoryRequirements.txt \
    $(MANDIR)/VkMemoryType.txt \
    $(MANDIR)/VkOffset2D.txt \
    $(MANDIR)/VkOffset3D.txt \
    $(MANDIR)/VkPhysicalDeviceMemoryProperties.txt \
    $(MANDIR)/VkPhysicalDeviceProperties.txt \
    $(MANDIR)/VkPhysicalDeviceSparseProperties.txt \
    $(MANDIR)/VkPipelineCacheCreateInfo.txt \
    $(MANDIR)/VkPipelineColorBlendAttachmentState.txt \
    $(MANDIR)/VkPipelineColorBlendStateCreateInfo.txt \
    $(MANDIR)/VkPipelineDepthStencilStateCreateInfo.txt \
    $(MANDIR)/VkPipelineDynamicStateCreateInfo.txt \
    $(MANDIR)/VkPipelineInputAssemblyStateCreateInfo.txt \
    $(MANDIR)/VkPipelineMultisampleStateCreateInfo.txt \
    $(MANDIR)/VkPipelineRasterizationStateCreateInfo.txt \
    $(MANDIR)/VkPipelineShaderStageCreateInfo.txt \
    $(MANDIR)/VkPipelineTessellationStateCreateInfo.txt \
    $(MANDIR)/VkPipelineVertexInputStateCreateInfo.txt \
    $(MANDIR)/VkPipelineViewportStateCreateInfo.txt \
    $(MANDIR)/VkPushConstantRange.txt \
    $(MANDIR)/VkQueryPoolCreateInfo.txt \
    $(MANDIR)/VkRect2D.txt \
    $(MANDIR)/VkRenderPassBeginInfo.txt \
    $(MANDIR)/VkRenderPassCreateInfo.txt \
    $(MANDIR)/VkSamplerCreateInfo.txt \
    $(MANDIR)/VkSemaphoreCreateInfo.txt \
    $(MANDIR)/VkShaderModuleCreateInfo.txt \
    $(MANDIR)/VkSparseBufferMemoryBindInfo.txt \
    $(MANDIR)/VkSparseImageFormatProperties.txt \
    $(MANDIR)/VkSparseImageMemoryBindInfo.txt \
    $(MANDIR)/VkSparseImageMemoryBind.txt \
    $(MANDIR)/VkSparseImageMemoryRequirements.txt \
    $(MANDIR)/VkSparseImageOpaqueMemoryBindInfo.txt \
    $(MANDIR)/VkSparseMemoryBind.txt \
    $(MANDIR)/VkSpecializationInfo.txt \
    $(MANDIR)/VkSpecializationMapEntry.txt \
    $(MANDIR)/VkStencilOpState.txt \
    $(MANDIR)/VkSubmitInfo.txt \
    $(MANDIR)/VkSubpassDependency.txt \
    $(MANDIR)/VkSubpassDescription.txt \
    $(MANDIR)/VkSubresourceLayout.txt \
    $(MANDIR)/VkVertexInputAttributeDescription.txt \
    $(MANDIR)/VkVertexInputBindingDescription.txt \
    $(MANDIR)/VkViewport.txt

FLAGSSOURCES=\
    $(MANDIR)/VkBufferCreateFlags.txt \
    $(MANDIR)/VkBufferUsageFlags.txt \
    $(MANDIR)/VkFormatFeatureFlags.txt \
    $(MANDIR)/VkImageCreateFlags.txt \
    $(MANDIR)/VkImageUsageFlags.txt \
    $(MANDIR)/VkMemoryPropertyFlags.txt \
    $(MANDIR)/VkPipelineStageFlags.txt \
    $(MANDIR)/VkQueryControlFlags.txt \
    $(MANDIR)/VkQueryResultFlags.txt \
    $(MANDIR)/VkQueueFlags.txt \
    $(MANDIR)/VkAccessFlags.txt \
    $(MANDIR)/VkAttachmentDescriptionFlags.txt \
    $(MANDIR)/VkBufferViewCreateFlags.txt \
    $(MANDIR)/VkColorComponentFlags.txt \
    $(MANDIR)/VkCommandBufferResetFlags.txt \
    $(MANDIR)/VkCommandBufferUsageFlags.txt \
    $(MANDIR)/VkCommandPoolCreateFlags.txt \
    $(MANDIR)/VkCommandPoolResetFlags.txt \
    $(MANDIR)/VkCullModeFlags.txt \
    $(MANDIR)/VkDependencyFlags.txt \
    $(MANDIR)/VkDescriptorPoolCreateFlags.txt \
    $(MANDIR)/VkDescriptorPoolResetFlags.txt \
    $(MANDIR)/VkDescriptorSetLayoutCreateFlags.txt \
    $(MANDIR)/VkDeviceCreateFlags.txt \
    $(MANDIR)/VkDeviceQueueCreateFlags.txt \
    $(MANDIR)/VkEventCreateFlags.txt \
    $(MANDIR)/VkFenceCreateFlags.txt \
    $(MANDIR)/VkFramebufferCreateFlags.txt \
    $(MANDIR)/VkImageAspectFlags.txt \
    $(MANDIR)/VkImageViewCreateFlags.txt \
    $(MANDIR)/VkInstanceCreateFlags.txt \
    $(MANDIR)/VkMemoryHeapFlags.txt \
    $(MANDIR)/VkMemoryMapFlags.txt \
    $(MANDIR)/VkPipelineCacheCreateFlags.txt \
    $(MANDIR)/VkPipelineColorBlendStateCreateFlags.txt \
    $(MANDIR)/VkPipelineCreateFlags.txt \
    $(MANDIR)/VkPipelineDepthStencilStateCreateFlags.txt \
    $(MANDIR)/VkPipelineDynamicStateCreateFlags.txt \
    $(MANDIR)/VkPipelineInputAssemblyStateCreateFlags.txt \
    $(MANDIR)/VkPipelineLayoutCreateFlags.txt \
    $(MANDIR)/VkPipelineMultisampleStateCreateFlags.txt \
    $(MANDIR)/VkPipelineRasterizationStateCreateFlags.txt \
    $(MANDIR)/VkPipelineShaderStageCreateFlags.txt \
    $(MANDIR)/VkPipelineTessellationStateCreateFlags.txt \
    $(MANDIR)/VkPipelineVertexInputStateCreateFlags.txt \
    $(MANDIR)/VkPipelineViewportStateCreateFlags.txt \
    $(MANDIR)/VkQueryPipelineStatisticFlags.txt \
    $(MANDIR)/VkQueryPoolCreateFlags.txt \
    $(MANDIR)/VkRenderPassCreateFlags.txt \
    $(MANDIR)/VkSampleCountFlags.txt \
    $(MANDIR)/VkSamplerCreateFlags.txt \
    $(MANDIR)/VkSemaphoreCreateFlags.txt \
    $(MANDIR)/VkShaderModuleCreateFlags.txt \
    $(MANDIR)/VkShaderStageFlags.txt \
    $(MANDIR)/VkSparseImageFormatFlags.txt \
    $(MANDIR)/VkSparseMemoryBindFlags.txt \
    $(MANDIR)/VkStencilFaceFlags.txt \
    $(MANDIR)/VkSubpassDescriptionFlags.txt

ENUMSOURCES=\
    $(MANDIR)/VkDescriptorType.txt \
    $(MANDIR)/VkImageLayout.txt \
    $(MANDIR)/VkImageType.txt \
    $(MANDIR)/VkImageViewType.txt \
    $(MANDIR)/VkSharingMode.txt \
    $(MANDIR)/VkAccessFlagBits.txt \
    $(MANDIR)/VkAttachmentDescriptionFlagBits.txt \
    $(MANDIR)/VkAttachmentLoadOp.txt \
    $(MANDIR)/VkAttachmentStoreOp.txt \
    $(MANDIR)/VkBlendFactor.txt \
    $(MANDIR)/VkBlendOp.txt \
    $(MANDIR)/VkBorderColor.txt \
    $(MANDIR)/VkBufferCreateFlagBits.txt \
    $(MANDIR)/VkBufferUsageFlagBits.txt \
    $(MANDIR)/VkColorComponentFlagBits.txt \
    $(MANDIR)/VkCommandBufferLevel.txt \
    $(MANDIR)/VkCommandBufferResetFlagBits.txt \
    $(MANDIR)/VkCommandBufferUsageFlagBits.txt \
    $(MANDIR)/VkCommandPoolCreateFlagBits.txt \
    $(MANDIR)/VkCommandPoolResetFlagBits.txt \
    $(MANDIR)/VkCompareOp.txt \
    $(MANDIR)/VkComponentSwizzle.txt \
    $(MANDIR)/VkCullModeFlagBits.txt \
    $(MANDIR)/VkDependencyFlagBits.txt \
    $(MANDIR)/VkDescriptorPoolCreateFlagBits.txt \
    $(MANDIR)/VkDynamicState.txt \
    $(MANDIR)/VkFenceCreateFlagBits.txt \
    $(MANDIR)/VkFilter.txt \
    $(MANDIR)/VkFormatFeatureFlagBits.txt \
    $(MANDIR)/VkFormat.txt \
    $(MANDIR)/VkFrontFace.txt \
    $(MANDIR)/VkImageAspectFlagBits.txt \
    $(MANDIR)/VkImageCreateFlagBits.txt \
    $(MANDIR)/VkImageTiling.txt \
    $(MANDIR)/VkImageUsageFlagBits.txt \
    $(MANDIR)/VkIndexType.txt \
    $(MANDIR)/VkInternalAllocationType.txt \
    $(MANDIR)/VkLogicOp.txt \
    $(MANDIR)/VkMemoryHeapFlagBits.txt \
    $(MANDIR)/VkMemoryPropertyFlagBits.txt \
    $(MANDIR)/VkPhysicalDeviceType.txt \
    $(MANDIR)/VkPipelineBindPoint.txt \
    $(MANDIR)/VkPipelineCacheHeaderVersion.txt \
    $(MANDIR)/VkPipelineCreateFlagBits.txt \
    $(MANDIR)/VkPipelineStageFlagBits.txt \
    $(MANDIR)/VkPolygonMode.txt \
    $(MANDIR)/VkPrimitiveTopology.txt \
    $(MANDIR)/VkQueryControlFlagBits.txt \
    $(MANDIR)/VkQueryPipelineStatisticFlagBits.txt \
    $(MANDIR)/VkQueryResultFlagBits.txt \
    $(MANDIR)/VkQueryType.txt \
    $(MANDIR)/VkQueueFlagBits.txt \
    $(MANDIR)/VkResult.txt \
    $(MANDIR)/VkSampleCountFlagBits.txt \
    $(MANDIR)/VkSamplerAddressMode.txt \
    $(MANDIR)/VkSamplerMipmapMode.txt \
    $(MANDIR)/VkShaderStageFlagBits.txt \
    $(MANDIR)/VkSparseImageFormatFlagBits.txt \
    $(MANDIR)/VkSparseMemoryBindFlagBits.txt \
    $(MANDIR)/VkStencilFaceFlagBits.txt \
    $(MANDIR)/VkStencilOp.txt \
    $(MANDIR)/VkStructureType.txt \
    $(MANDIR)/VkSubpassContents.txt \
    $(MANDIR)/VkSystemAllocationScope.txt \
    $(MANDIR)/VkVertexInputRate.txt

MANSOURCES=$(FUNCSOURCES) $(STRUCTSOURCES) $(FLAGSSOURCES) $(ENUMSOURCES) $(WSISOURCES) $(EXTSOURCES)

MANPAGEDIR=$(OUTDIR)/man/$(MANSECTION)
MANPAGES=$(MANSOURCES:$(MANDIR)/%.txt=$(MANPAGEDIR)/%.$(MANSECTION))
MANHTMLDIR=$(OUTDIR)/man/html
MANHTML=$(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)

manpagesall: manpages manhtmlpages

manpages: $(MANPAGEDIR) $(MANPAGES)

manhtmlpages: $(MANHTMLDIR) $(MANHTML)

manhtmlpages: VKCONF=config/manpages.conf

# These dependencies don't take into account include directives

$(MANPAGEDIR)/%.$(MANSECTION): $(MANDIR)/%.$(MANSECTION)
	$(QUIET)mv $< $@

$(MANDIR)/%.$(MANSECTION): $(MANDIR)/%.txt $(MANDIR)/footer.txt config/manpages.conf
	$(QUIET)$(ECHO) Building $@
	$(QUIET)$(A2X) -d manpage -f manpage --asciidoc-opts "-f config/manpages.conf" $(A2XOPTS) $<

$(MANHTMLDIR)/%.html: $(MANDIR)/%.txt $(MANDIR)/footer.txt config/manpages.conf
	$(QUIET)$(ECHO) Building $@
	$(QUIET)$(A2X) -d manpage -f xhtml --asciidoc-opts "-f config/manpages.conf" --stylesheet=vkman.css $(A2XOPTS) --destination-dir=$(@D) $<

$(MANHTMLDIR):
	$(QUIET)$(MKDIR) $@

$(MANPAGEDIR):
	$(QUIET)$(MKDIR) $@

clean: cleanmanhtmlpages cleanmanpages

cleanmanhtmlpages:
	$(RM) $(MANHTML)
	$(RMRF) $(MANHTMLDIR)

cleanmanpages:
	$(RM) $(MANPAGES)
	$(RMRF) $(MANPAGEDIR)

.PHONY: $(MANHTMLDIR) $(MANPAGEDIR)

