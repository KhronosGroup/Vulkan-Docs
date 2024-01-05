---
name: Template for Release Task List
about: This template is used by release managers in the Vulkan working group to create
  release task lists for newly published specs.
title: ''
labels: ''
assignees: ''

---

<!--
- Copyright 2019-2024 The Khronos Group Inc.
-
- SPDX-License-Identifier: CC-BY-4.0
-
-->
Release Task List

<!-- This template is used by release managers in the Vulkan working group
to create release task list issues for newly published specs.
To fill one out, delete checkbox lines for irrelevant items
(such as glslang support for extensions that do not affect SPIR-V)
and replace markdown comments with the item they
call for. In the case of deliverables, you can also check
the box when you supply the appropriate link.-->

Title of issue:  Task list for <!-- VK API or extension --> release

<!-- Brief description of what the API or extension does and any context needed for why it exists. -->

The task list for the <!-- VK API or extension name --> release is:
<!-- Note: include relevant task list items only. -->

 - [ ] Vulkan Specification:  <!-- link to Vulkan registry entry-->
 - [ ] SPIRV specification:  <!-- link to SPIRV registry entry-->
 - [ ] SPIRV Headers:  <!-- link to SPIRV-Headers GitHub pull request -->
 - [ ] SPIRV tools released: <!-- link to SPIRV-Tools GitHub pull request -->
 - [ ] GLSL extension: <!-- link to GLSL GitHub pull request -->
 - [ ] Glslang implementation: <!-- link to glslgang GitHub pull request-->
 - [ ] Conformance tests released: <!-- link(s) to VK-GL-CTS GitHub releases -->
 - [ ] SDK released: <!-- link to SDK (list version number) -->

     - [ ] Validation layer: <!-- link to Vulkan-ValidationLayers GitHub pull request -->
     - [ ] Emulation layer: <!-- link to Vulkan-ExtensionLayer GitHub pull request -->

 - [ ] Vulkan Guide:  <!-- Link to Vulkan-Guide chapter -->
 - [ ] API Examples:  <!-- Link to API examples in Vulkan-Docs/wiki -->
 - [ ] Shaderc:  <!-- Link to shaderc GitHub pull request -->
 - [ ] HLSL mapping:
 - [ ] HLSL glslang support:
 - [ ] HLSL DXC support: <!-- link to DXC GitHub pull request -->

As each component is made public, the task will be checked off. When all tasks have been completed this issue will be closed and the extension will be fully released.
