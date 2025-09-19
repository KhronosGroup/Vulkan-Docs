#!/bin/bash
# Copyright 2025 The Khronos Group Inc.
# SPDX-License-Identifier: Apache-2.0

# Update queues= attributes to use the API bitnames instead of colloquial
# short versions.
# This can be used when updating an out of date branch:
#   scripts/updateQueueNames.sh xml/vk.xml
# See gitlab issue #4393
sed -E -i \
    -e 's/(queues="[^"]*)graphics/\1VK_QUEUE_GRAPHICS_BIT/' \
    -e 's/(queues="[^"]*)compute/\1VK_QUEUE_COMPUTE_BIT/' \
    -e 's/(queues="[^"]*)transfer/\1VK_QUEUE_TRANSFER_BIT/' \
    -e 's/(queues="[^"]*)sparse_binding/\1VK_QUEUE_SPARSE_BINDING_BIT/' \
    -e 's/(queues="[^"]*)decode/\1VK_QUEUE_VIDEO_DECODE_BIT_KHR/' \
    -e 's/(queues="[^"]*)encode/\1VK_QUEUE_VIDEO_ENCODE_BIT_KHR/' \
    -e 's/(queues="[^"]*)opticalflow/\1VK_QUEUE_OPTICAL_FLOW_BIT_NV/' \
    -e 's/(queues="[^"]*)data_graph/\1VK_QUEUE_DATA_GRAPH_BIT_ARM/' \
    $*
