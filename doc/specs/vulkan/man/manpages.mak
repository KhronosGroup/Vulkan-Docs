MANDIR?=.
MANSECTION:=3

WSISOURCES=\
    $(MANDIR)/vkAcquireNextImageKHR.txt                                        \
    $(MANDIR)/vkCreateAndroidSurfaceKHR.txt                                    \
    $(MANDIR)/vkCreateDisplayModeKHR.txt                                       \
    $(MANDIR)/vkCreateDisplayPlaneSurfaceKHR.txt                               \
    $(MANDIR)/vkCreateMirSurfaceKHR.txt                                        \
    $(MANDIR)/vkCreateSharedSwapchainsKHR.txt                                  \
    $(MANDIR)/vkCreateSwapchainKHR.txt                                         \
    $(MANDIR)/vkCreateWaylandSurfaceKHR.txt                                    \
    $(MANDIR)/vkCreateWin32SurfaceKHR.txt                                      \
    $(MANDIR)/vkCreateXcbSurfaceKHR.txt                                        \
    $(MANDIR)/vkCreateXlibSurfaceKHR.txt                                       \
    $(MANDIR)/vkDestroySurfaceKHR.txt                                          \
    $(MANDIR)/vkDestroySwapchainKHR.txt                                        \
    $(MANDIR)/vkGetDisplayModePropertiesKHR.txt                                \
    $(MANDIR)/vkGetDisplayPlaneCapabilitiesKHR.txt                             \
    $(MANDIR)/vkGetDisplayPlaneSupportedDisplaysKHR.txt                        \
    $(MANDIR)/vkGetPhysicalDeviceDisplayPlanePropertiesKHR.txt                 \
    $(MANDIR)/vkGetPhysicalDeviceDisplayPropertiesKHR.txt                      \
    $(MANDIR)/vkGetPhysicalDeviceMirPresentationSupportKHR.txt                 \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceCapabilitiesKHR.txt                    \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceFormatsKHR.txt                         \
    $(MANDIR)/vkGetPhysicalDeviceSurfacePresentModesKHR.txt                    \
    $(MANDIR)/vkGetPhysicalDeviceSurfaceSupportKHR.txt                         \
    $(MANDIR)/vkGetPhysicalDeviceWaylandPresentationSupportKHR.txt             \
    $(MANDIR)/vkGetPhysicalDeviceWin32PresentationSupportKHR.txt               \
    $(MANDIR)/vkGetPhysicalDeviceXcbPresentationSupportKHR.txt                 \
    $(MANDIR)/vkGetPhysicalDeviceXlibPresentationSupportKHR.txt                \
    $(MANDIR)/vkGetSwapchainImagesKHR.txt                                      \
    $(MANDIR)/vkQueuePresentKHR.txt                                            \

FUNCSOURCES=\
    $(MANDIR)/vkAllocateCommandBuffers.txt                                     \
    $(MANDIR)/vkAllocateDescriptorSets.txt                                     \
    $(MANDIR)/vkAllocateMemory.txt                                             \
    $(MANDIR)/vkBeginCommandBuffer.txt                                         \
    $(MANDIR)/vkBindBufferMemory.txt                                           \
    $(MANDIR)/vkBindImageMemory.txt                                            \
    $(MANDIR)/vkCmdBeginQuery.txt                                              \
    $(MANDIR)/vkCmdBeginRenderPass.txt                                         \
    $(MANDIR)/vkCmdBindDescriptorSets.txt                                      \
    $(MANDIR)/vkCmdBindIndexBuffer.txt                                         \
    $(MANDIR)/vkCmdBindPipeline.txt                                            \
    $(MANDIR)/vkCmdBindVertexBuffers.txt                                       \
    $(MANDIR)/vkCmdBlitImage.txt                                               \
    $(MANDIR)/vkCmdClearAttachments.txt                                        \
    $(MANDIR)/vkCmdClearColorImage.txt                                         \
    $(MANDIR)/vkCmdClearDepthStencilImage.txt                                  \
    $(MANDIR)/vkCmdCopyBuffer.txt                                              \
    $(MANDIR)/vkCmdCopyBufferToImage.txt                                       \
    $(MANDIR)/vkCmdCopyImage.txt                                               \
    $(MANDIR)/vkCmdCopyImageToBuffer.txt                                       \
    $(MANDIR)/vkCmdCopyQueryPoolResults.txt                                    \
    $(MANDIR)/vkCmdDispatch.txt                                                \
    $(MANDIR)/vkCmdDispatchIndirect.txt                                        \
    $(MANDIR)/vkCmdDraw.txt                                                    \
    $(MANDIR)/vkCmdDrawIndexed.txt                                             \
    $(MANDIR)/vkCmdDrawIndexedIndirect.txt                                     \
    $(MANDIR)/vkCmdDrawIndirect.txt                                            \
    $(MANDIR)/vkCmdEndQuery.txt                                                \
    $(MANDIR)/vkCmdEndRenderPass.txt                                           \
    $(MANDIR)/vkCmdExecuteCommands.txt                                         \
    $(MANDIR)/vkCmdFillBuffer.txt                                              \
    $(MANDIR)/vkCmdNextSubpass.txt                                             \
    $(MANDIR)/vkCmdPipelineBarrier.txt                                         \
    $(MANDIR)/vkCmdPushConstants.txt                                           \
    $(MANDIR)/vkCmdResetEvent.txt                                              \
    $(MANDIR)/vkCmdResetQueryPool.txt                                          \
    $(MANDIR)/vkCmdResolveImage.txt                                            \
    $(MANDIR)/vkCmdSetBlendConstants.txt                                       \
    $(MANDIR)/vkCmdSetDepthBias.txt                                            \
    $(MANDIR)/vkCmdSetDepthBounds.txt                                          \
    $(MANDIR)/vkCmdSetEvent.txt                                                \
    $(MANDIR)/vkCmdSetLineWidth.txt                                            \
    $(MANDIR)/vkCmdSetScissor.txt                                              \
    $(MANDIR)/vkCmdSetStencilCompareMask.txt                                   \
    $(MANDIR)/vkCmdSetStencilReference.txt                                     \
    $(MANDIR)/vkCmdSetStencilWriteMask.txt                                     \
    $(MANDIR)/vkCmdSetViewport.txt                                             \
    $(MANDIR)/vkCmdUpdateBuffer.txt                                            \
    $(MANDIR)/vkCmdWaitEvents.txt                                              \
    $(MANDIR)/vkCmdWriteTimestamp.txt                                          \
    $(MANDIR)/vkCreateBuffer.txt                                               \
    $(MANDIR)/vkCreateBufferView.txt                                           \
    $(MANDIR)/vkCreateCommandPool.txt                                          \
    $(MANDIR)/vkCreateComputePipelines.txt                                     \
    $(MANDIR)/vkCreateDescriptorPool.txt                                       \
    $(MANDIR)/vkCreateDescriptorSetLayout.txt                                  \
    $(MANDIR)/vkCreateDevice.txt                                               \
    $(MANDIR)/vkCreateEvent.txt                                                \
    $(MANDIR)/vkCreateFence.txt                                                \
    $(MANDIR)/vkCreateFramebuffer.txt                                          \
    $(MANDIR)/vkCreateGraphicsPipelines.txt                                    \
    $(MANDIR)/vkCreateImage.txt                                                \
    $(MANDIR)/vkCreateImageView.txt                                            \
    $(MANDIR)/vkCreateInstance.txt                                             \
    $(MANDIR)/vkCreatePipelineCache.txt                                        \
    $(MANDIR)/vkCreatePipelineLayout.txt                                       \
    $(MANDIR)/vkCreateQueryPool.txt                                            \
    $(MANDIR)/vkCreateRenderPass.txt                                           \
    $(MANDIR)/vkCreateSampler.txt                                              \
    $(MANDIR)/vkCreateSemaphore.txt                                            \
    $(MANDIR)/vkCreateShaderModule.txt                                         \
    $(MANDIR)/vkDestroyBuffer.txt                                              \
    $(MANDIR)/vkDestroyBufferView.txt                                          \
    $(MANDIR)/vkDestroyCommandPool.txt                                         \
    $(MANDIR)/vkDestroyDescriptorPool.txt                                      \
    $(MANDIR)/vkDestroyDescriptorSetLayout.txt                                 \
    $(MANDIR)/vkDestroyDevice.txt                                              \
    $(MANDIR)/vkDestroyEvent.txt                                               \
    $(MANDIR)/vkDestroyFence.txt                                               \
    $(MANDIR)/vkDestroyFramebuffer.txt                                         \
    $(MANDIR)/vkDestroyImage.txt                                               \
    $(MANDIR)/vkDestroyImageView.txt                                           \
    $(MANDIR)/vkDestroyInstance.txt                                            \
    $(MANDIR)/vkDestroyPipeline.txt                                            \
    $(MANDIR)/vkDestroyPipelineCache.txt                                       \
    $(MANDIR)/vkDestroyPipelineLayout.txt                                      \
    $(MANDIR)/vkDestroyQueryPool.txt                                           \
    $(MANDIR)/vkDestroyRenderPass.txt                                          \
    $(MANDIR)/vkDestroySampler.txt                                             \
    $(MANDIR)/vkDestroySemaphore.txt                                           \
    $(MANDIR)/vkDestroyShaderModule.txt                                        \
    $(MANDIR)/vkDeviceWaitIdle.txt                                             \
    $(MANDIR)/vkEndCommandBuffer.txt                                           \
    $(MANDIR)/vkEnumerateDeviceExtensionProperties.txt                         \
    $(MANDIR)/vkEnumerateDeviceLayerProperties.txt                             \
    $(MANDIR)/vkEnumerateInstanceExtensionProperties.txt                       \
    $(MANDIR)/vkEnumerateInstanceLayerProperties.txt                           \
    $(MANDIR)/vkEnumeratePhysicalDevices.txt                                   \
    $(MANDIR)/vkFlushMappedMemoryRanges.txt                                    \
    $(MANDIR)/vkFreeCommandBuffers.txt                                         \
    $(MANDIR)/vkFreeDescriptorSets.txt                                         \
    $(MANDIR)/vkFreeMemory.txt                                                 \
    $(MANDIR)/vkGetBufferMemoryRequirements.txt                                \
    $(MANDIR)/vkGetDeviceMemoryCommitment.txt                                  \
    $(MANDIR)/vkGetDeviceProcAddr.txt                                          \
    $(MANDIR)/vkGetDeviceQueue.txt                                             \
    $(MANDIR)/vkGetEventStatus.txt                                             \
    $(MANDIR)/vkGetFenceStatus.txt                                             \
    $(MANDIR)/vkGetImageMemoryRequirements.txt                                 \
    $(MANDIR)/vkGetImageSparseMemoryRequirements.txt                           \
    $(MANDIR)/vkGetImageSubresourceLayout.txt                                  \
    $(MANDIR)/vkGetInstanceProcAddr.txt                                        \
    $(MANDIR)/vkGetPhysicalDeviceFeatures.txt                                  \
    $(MANDIR)/vkGetPhysicalDeviceFormatProperties.txt                          \
    $(MANDIR)/vkGetPhysicalDeviceImageFormatProperties.txt                     \
    $(MANDIR)/vkGetPhysicalDeviceMemoryProperties.txt                          \
    $(MANDIR)/vkGetPhysicalDeviceProperties.txt                                \
    $(MANDIR)/vkGetPhysicalDeviceQueueFamilyProperties.txt                     \
    $(MANDIR)/vkGetPhysicalDeviceSparseImageFormatProperties.txt               \
    $(MANDIR)/vkGetPipelineCacheData.txt                                       \
    $(MANDIR)/vkGetQueryPoolResults.txt                                        \
    $(MANDIR)/vkGetRenderAreaGranularity.txt                                   \
    $(MANDIR)/vkInvalidateMappedMemoryRanges.txt                               \
    $(MANDIR)/vkMapMemory.txt                                                  \
    $(MANDIR)/vkMergePipelineCaches.txt                                        \
    $(MANDIR)/vkQueueBindSparse.txt                                            \
    $(MANDIR)/vkQueueSubmit.txt                                                \
    $(MANDIR)/vkQueueWaitIdle.txt                                              \
    $(MANDIR)/vkResetCommandBuffer.txt                                         \
    $(MANDIR)/vkResetCommandPool.txt                                           \
    $(MANDIR)/vkResetDescriptorPool.txt                                        \
    $(MANDIR)/vkResetEvent.txt                                                 \
    $(MANDIR)/vkResetFences.txt                                                \
    $(MANDIR)/vkSetEvent.txt                                                   \
    $(MANDIR)/vkUnmapMemory.txt                                                \
    $(MANDIR)/vkUpdateDescriptorSets.txt                                       \
    $(MANDIR)/vkWaitForFences.txt                                              \

STRUCTSOURCES=\
    $(MANDIR)/VkAllocationCallbacks.txt \
    $(MANDIR)/VkCommandBufferAllocateInfo.txt \
    $(MANDIR)/VkDescriptorSetAllocateInfo.txt \
    $(MANDIR)/VkBufferCreateInfo.txt \
    $(MANDIR)/VkBufferMemoryBarrier.txt \
    $(MANDIR)/VkImageCreateInfo.txt \
    $(MANDIR)/VkImageMemoryBarrier.txt \
    $(MANDIR)/VkMemoryAllocateInfo.txt \
    $(MANDIR)/VkPhysicalDeviceFeatures.txt \
    $(MANDIR)/VkPhysicalDeviceLimits.txt \
    $(MANDIR)/VkPipelineLayoutCreateInfo.txt \
    $(MANDIR)/VkQueueFamilyProperties.txt \
    $(MANDIR)/VkWriteDescriptorSet.txt

FLAGSSOURCES=\
    $(MANDIR)/VkBufferCreateFlags.txt \
    $(MANDIR)/VkBufferUsageFlags.txt \
    $(MANDIR)/VkFormatFeatureFlags.txt \
    $(MANDIR)/VkImageCreateFlags.txt \
    $(MANDIR)/VkImageUsageFlags.txt \
    $(MANDIR)/VkMemoryInputFlags.txt \
    $(MANDIR)/VkMemoryOutputFlags.txt \
    $(MANDIR)/VkMemoryPropertyFlags.txt \
    $(MANDIR)/VkPipelineStageFlags.txt \
    $(MANDIR)/VkQueryControlFlags.txt \
    $(MANDIR)/VkQueryResultFlags.txt \
    $(MANDIR)/VkQueueFlags.txt

ENUMSOURCES=\
    $(MANDIR)/VkDescriptorType.txt \
    $(MANDIR)/VkImageLayout.txt \
    $(MANDIR)/VkImageType.txt \
    $(MANDIR)/VkImageViewType.txt \
    $(MANDIR)/VkSharingMode.txt

MANSOURCES=$(FUNCSOURCES) $(STRUCTSOURCES) $(FLAGSSOURCES) $(ENUMSOURCES)

MANPAGEDIR=$(OUTDIR)/man/$(MANSECTION)
MANPAGES=$(MANSOURCES:$(MANDIR)/%.txt=$(MANPAGEDIR)/%.$(MANSECTION))
MANHTMLDIR=$(OUTDIR)/man/html
MANHTML=$(MANSOURCES:$(MANDIR)/%.txt=$(MANHTMLDIR)/%.html)

manpagesall: manpages manhtmlpages

manpages: $(MANPAGEDIR) $(MANPAGES)

manhtmlpages: $(MANHTMLDIR) $(MANHTML)

manhtmlpages: VKCONF=config/manpages.conf

# These dependencies don't take into account include directives

$(MANPAGEDIR)/%.$(MANSECTION): $(MANDIR)/%.txt $(MANDIR)/footer.txt config/manpages.conf
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

