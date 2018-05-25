# What Happened To The Vulkan Extension Loader?

If you're looking for the files vulkan_ext.[ch] in this directory, they have
been removed. There were two significant problems with these simple
wrappers.

First, vulkan_ext exported all extension entrypoints. However, the Vulkan
loader also exports entrypoints for the window system integration
extensions. If someone tried to compile a project and link it to both the
loader and vulkan_ext, they would get a bunch of redefined symbols. This
linking error is difficult to work around, because vulkan_ext does not have
an easy method of disabling the entrypoints at compile time. It is possible
to remove these entrypoints when generating vulkan_ext, but even then you
have to manually compile a list of every single extension to be disabled.

Second, each entrypoint is only stored once, regardless of how many
instances or devices are created. This means that attempting to use multiple
instances or devices in parallel can result in one device calling function
pointers that are only valid on the other device, which will crash. You may
be able to work around this by never initializing the device dispatch
(vkExtInitDevice), but we haven't tried this.

It is still possible to retrieve the last versions of these files in the
Github KhronosGroup/Vulkan-Docs repository from the 'v1.1.75' release tag.
It is also possible to regenerate them from ../../xml/vk.xml, although we
are no longer maintaining the generator code and it may eventually stop
working correctly. See README.adoc and the `extloader` Makefile target in
that directory.
