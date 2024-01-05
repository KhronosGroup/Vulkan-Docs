<!--
Copyright 2018-2024 The Khronos Group Inc.

SPDX-License-Identifier: CC-BY-4.0
-->

<!-- Vulkan EXT Extension Development Checklist Template -->

<!--
This template captures requirements checklists for key milestones
a Vulkan EXT extension passes as it moves from development to
release. You should create an issue from this template
when there is reasonable consensus in the working group that the
extension should be created.

As progress is made on work items, fill in the italicized fields with
appropriate data. For example, when a merge request exists, edit it
into the "API specification ready" line in place of _MR_. When the WG
agrees that it is ready for release, check off the item in
the checklist.
("Ready for release" implies that all discussions are
resolved and there are no MRs in flight that modify behavior defined
by the extension and its dependencies.)

Not all requirements are relevant to all extensions. For example, an
extension that has no language dependencies will not need SPIR-V /
GLSL / HLSL items. In such cases, check the item off and write "N/A"
in the associated data fields. Requirements may also be checked off
if waived by vote of the working group, with a 2/3 majority of
non-abstaining vote are in favor.

-->

## Preconditions for creating public release issue on GitHub

<!--
Check off any of the following preconditions that are not relevant to
the extension in question. Enter target dates for software artifacts
where indicated.
-->

 - [ ] Vulkan API specification stable in extension branch, with no substantial changes expected (_MR_)
 - [ ] VAP consulted to the extent the WG considers appropriate (_VAP issue, WG discussion, or email thread_)
 - [ ] API spec naming review complete (_date_)
 - [ ] CTS tests approved with three passing implementations (_CTS request issue_, _gerrit cl_)
 - [ ] SPIR-V specification ready for release (_MR_)
 - [ ] GLSL specification ready for release (_MR_)
 - [ ] Developer guidance language approved (_date_)
 - [ ] GLSLang implementation ready for release (_MR_)
 - [ ] Validation compatibility changes ready for release (_MR_)
 - [ ] Validation new VU changes ready for release (_MR_ or _request issue_ if deferred)
 - [ ] Loader support (for instance extensions) release for release (_MR_)
 - [ ] HLSL mapping defined
 - [ ] HLSL glslang support release schedule agreed: target _target-date_
 - [ ] HLSL DXC support release schedule agreed: target _target-date_
 - [ ] CTS release schedule agreed: target _target-date_
 - [ ] SDK release schedule agreed: target _target-date_
 - [ ] SPIR-V tools implementation schedule agreed: target _target-date_
 - [ ] Public release schedule agreed: target _target-date_

## Preconditions for closing this issue

 - [ ] Public release issue created (_URL_)
 - [ ] Public release issue items checked off and issue closed
