
# _Vulkan Feature Development Checklist Template_

_This template captures checklists for the stages of development that
a Vulkan KHR extension passes through as it moves from development to
ratification and release. You should create an issue from this template
when the extension draft is stable and there is reasonable consensus in
the working group that it is on a path to ratification._

_Edit the template to suit the extension you are considering (and to
delete the italicized instructions). Delete any requirements that are not
relevant; for example, an extension that has no language dependencies
will not need SPIR-V / GLSL / HLSL items, and an EXT GLSL extension
will not require Promoter ratification._

_Requirements may be waived by vote of of the working group, provided
that a 2/3 majority of non-abstaining vote are in favor._

# Release checklist for _VK_KHR_extension_name_here_

## Preconditions for Call for Votes (CfV)

_A formal CfV is issued following agreement at a Tuesday meeting that a
vote should be held at the following Tuesday meeting. Preconditions
for a CfV are as follows; "specification stable" means that there are
no MRs in flight that modify behavior defined by the extension and its
dependencies. Delete any of the following preconditions that are not relevant to
the extension in question_


 - [ ] VAP consulted to the extent the WG considers appropriate
 - [ ] CTS tests approved with three passing implementations
 - [ ] Vulkan specification merged and stable in devel
 - [ ] SPIR-V specification merged and stable
 - [ ] GLSL specification merged and stable

## Preconditions for submission to Promoters

 - [ ] WG vote to submit passed with a 3/4 majority
 - [ ] Submission package available for Promoter review

## Preconditions for creating public release issue on GitHub

_Delete any of the following preconditions that are not relevant to
the extension in question_

 - [ ] Vulkan specification ratified by Promoters
 - [ ] SPIR-V specification ratified by Promoters
 - [ ] GLSL specification ratified by Promoters
 - [ ] GLSLang implementation approved to merge
 - [ ] Marketing summary written and approved by Vulkan WG and PR team
 - [ ] Validation layer implementation approved to merge
 - [ ] HLSL mapping defined
 - [ ] HLSL mapping supported in GLSLang
 - [ ] HLSL mapping supported in DXC
 - [ ] CTS tests approved to merge
 - [ ] SPIR-V tools implementation approved to merge
 - [ ] Loader support approved to merge (for instance extensions)
 - [ ] Public release approved by Vulkan WG

## Preconditions for closing this issue

 - [ ] Public release issue items checked off and issue closed

## Additional (Optional) Items 

_These additional items are recommended for creation at some
point during or after the release, but are not required at any point._

 - [ ] Usage Examples
 - [ ] Usage Advice
