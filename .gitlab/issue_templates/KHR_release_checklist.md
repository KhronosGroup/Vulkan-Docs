<!--
Copyright 2018-2024 The Khronos Group Inc.

SPDX-License-Identifier: CC-BY-4.0
-->


<!-- Vulkan KHR Extension Development Checklist Template -->

<!--
This template captures requirements checklists for key milestones
a Vulkan KHR extension passes as it moves from development to
ratification and release. You should create an issue from this template
when there is reasonable consensus in the working group that the
extension should be created.

As progress is made on work items, fill in the italicized fields with
appropriate data. For example, when a merge request exists, edit it
into the "API specification ready" line in place of _MR_.  When the WG
agrees that it ready for a ratification vote, check off the item in
the checklist.
("Ready for ratification" implies that all discussions are
resolved and there are no MRs in flight that modify behavior defined
by the extension or its dependencies.)

Not all requirements are relevant to all extensions. For example, an
extension that has no language dependencies will not need SPIR-V /
GLSL / HLSL items. In such cases, check the item off and write "N/A"
in the associated data fields. Requirements may also be checked off
if waived by vote of the working group, with a 2/3 majority of
non-abstaining vote are in favor.
-->

## Preconditions for Call for Votes (CfV)

<!--
A formal CfV is issued following agreement at a Tuesday meeting that a
vote should be held at the following Tuesday meeting. Preconditions
for a CfV are as follows:
-->

 - [ ] Vulkan API specification stable in extension branch, with no substantial changes expected (_MR_)
 - [ ] VAP consulted to the extent the WG considers appropriate (_VAP issue, WG discussion, or email thread_)
 - [ ] API spec naming review complete (_date_)
 - [ ] CTS tests approved with three passing implementations (_CTS request issue_, _gerrit cl_)
 - [ ] SPIR-V specification ready for ratification (_MR_)
 - [ ] GLSL specification ready for release (_MR_)
 - [ ] Developer guidance language approved (_date_)

## Preconditions for submission to Promoters

 - [ ] WG vote to submit passed with a 3/4 majority (_date_)
 - [ ] Submission package available for Promoter review (_link_)

## Preconditions for creating public release issue on GitHub

<!--
Check off any of the following preconditions that are not relevant to
the extension in question. Enter target dates for software artifacts
where indicated.
-->

 - [ ] Vulkan specification ratified by Promoters (_date_)
 - [ ] SPIR-V specification ratified by Promoters (_date_)
 - [ ] GLSLang implementation ready for release (_MR_)
 - [ ] Validation compatibility changes ready for release (_MR_)
 - [ ] Validation new VU changes ready for release (_MR_ or _request issue_ if deferred)
 - [ ] Loader support (for instance extensions) ready for release (_MR_)
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
