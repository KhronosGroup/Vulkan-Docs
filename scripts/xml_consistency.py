#!/usr/bin/python3
#
# Copyright (c) 2019 Collabora, Ltd.
#
# SPDX-License-Identifier: Apache-2.0
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
#
# Purpose:      This script checks some "business logic" in the XML registry.

import re
import sys
from pathlib import Path

from check_spec_links import VulkanEntityDatabase as OrigEntityDatabase
from reg import Registry
from spec_tools.consistency_tools import XMLChecker
from spec_tools.util import findNamedElem, getElemName, getElemType
from vkconventions import VulkanConventions as APIConventions

# Most extensions have theier meta-enums named with just an uppercase version of their name,
# but some are weird.
EXTENSION_ENUM_NAME_SPELLING_CHANGE = {
    'VK_EXT_swapchain_colorspace': 'VK_EXT_SWAPCHAIN_COLOR_SPACE',
    'VK_KHR_get_physical_device_properties2': 'VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2',
    'VK_KHR_get_display_properties2': 'VK_KHR_GET_DISPLAY_PROPERTIES_2',
    'VK_KHR_get_surface_capabilities2': 'VK_KHR_GET_SURFACE_CAPABILITIES_2',
    'VK_KHR_create_renderpass2': 'VK_KHR_CREATE_RENDERPASS_2',
    'VK_KHR_bind_memory2': 'VK_KHR_BIND_MEMORY_2',
    'VK_KHR_get_memory_requirements2': 'VK_KHR_GET_MEMORY_REQUIREMENTS_2',
    'VK_AMD_shader_core_properties2': 'VK_AMD_SHADER_CORE_PROPERTIES_2',
    'VK_INTEL_shader_integer_functions2': 'VK_INTEL_SHADER_INTEGER_FUNCTIONS_2'
}


def get_extension_commands(reg):
    extension_cmds = set()
    for ext in reg.extensions:
        for cmd in ext.findall("./require/command[@name]"):
            extension_cmds.add(cmd.get("name"))
    return extension_cmds


def get_enum_value_names(reg, enum_type):
    names = set()
    result_elem = reg.groupdict[enum_type].elem
    for val in result_elem.findall("./enum[@name]"):
        names.add(val.get("name"))
    return names


DESTROY_PREFIX = "vkDestroy"
TYPEENUM = "VkStructureType"


SPECIFICATION_DIR = Path(__file__).parent.parent
REVISION_RE = re.compile(r' *[*] Revision (?P<num>[1-9][0-9]*),.*')


def get_extension_source(extname):
    fn = '{}.txt'.format(extname)
    return str(SPECIFICATION_DIR / 'appendices' / fn)


class EntityDatabase(OrigEntityDatabase):

    def makeRegistry(self):
        try:
            import lxml.etree as etree
            HAS_LXML = True
        except ImportError:
            HAS_LXML = False
        if not HAS_LXML:
            return super().makeRegistry()

        registryFile = str(SPECIFICATION_DIR / 'xml/vk.xml')
        registry = Registry()
        registry.filename = registryFile
        registry.loadElementTree(etree.parse(registryFile))
        return registry


class Checker(XMLChecker):
    def __init__(self):
        manual_types_to_codes = {
            # These are hard-coded "manual" return codes:
            # the codes of the value (string, list, or tuple)
            # are available for a command if-and-only-if
            # the key type is passed as an input.
            "VkFormat": "VK_ERROR_FORMAT_NOT_SUPPORTED"
        }
        forward_only = {
            # Like the above, but these are only valid in the
            # "type implies return code" direction
        }
        reverse_only = {
            # like the above, but these are only valid in the
            # "return code implies type or its descendant" direction
            # "XrDuration": "XR_TIMEOUT_EXPIRED"
        }
        # Some return codes are related in that only one of a set
        # may be returned by a command
        # (eg. XR_ERROR_SESSION_RUNNING and XR_ERROR_SESSION_NOT_RUNNING)
        self.exclusive_return_code_sets = tuple(
            # set(("XR_ERROR_SESSION_NOT_RUNNING", "XR_ERROR_SESSION_RUNNING")),
        )

        conventions = APIConventions()
        db = EntityDatabase()

        self.extension_cmds = get_extension_commands(db.registry)
        self.return_codes = get_enum_value_names(db.registry, 'VkResult')
        self.structure_types = get_enum_value_names(db.registry, TYPEENUM)

        # Dict of entity name to a list of messages to suppress. (Exclude any context data and "Warning:"/"Error:")
        # Keys are entity names, values are tuples or lists of message text to suppress.
        suppressions = {}

        # Initialize superclass
        super().__init__(entity_db=db, conventions=conventions,
                         manual_types_to_codes=manual_types_to_codes,
                         forward_only_types_to_codes=forward_only,
                         reverse_only_types_to_codes=reverse_only,
                         suppressions=suppressions)

    def check_command_return_codes_basic(self, name, info,
                                         successcodes, errorcodes):
        """Check a command's return codes for consistency.

        Called on every command."""
        # Check that all extension commands can return the code associated
        # with trying to use an extension that wasn't enabled.
        # if name in self.extension_cmds and UNSUPPORTED not in errorcodes:
        #     self.record_error("Missing expected return code",
        #                       UNSUPPORTED,
        #                       "implied due to being an extension command")

        codes = successcodes.union(errorcodes)

        # Check that all return codes are recognized.
        unrecognized = codes - self.return_codes
        if unrecognized:
            self.record_error("Unrecognized return code(s):",
                              unrecognized)

        elem = info.elem
        params = [(getElemName(elt), elt) for elt in elem.findall('param')]

        def is_count_output(name, elt):
            # Must end with Count or Size,
            # not be const,
            # and be a pointer (detected by naming convention)
            return (name.endswith('Count') or name.endswith('Size')) \
                and (elt.tail is None or 'const' not in elt.tail) \
                and (name.startswith('p'))

        countParams = [elt
                       for name, elt in params
                       if is_count_output(name, elt)]
        if countParams:
            assert(len(countParams) == 1)
            if 'VK_INCOMPLETE' not in successcodes:
                self.record_error(
                    "Apparent enumeration of an array without VK_INCOMPLETE in successcodes.")

        elif 'VK_INCOMPLETE' in successcodes:
            self.record_error(
                "VK_INCOMPLETE in successcodes of command that is apparently not an array enumeration.")

    def check_param(self, param):
        """Check a member of a struct or a param of a function.

        Called from check_params."""
        super().check_param(param)

        if not self.is_api_type(param):
            return

        param_text = "".join(param.itertext())
        param_name = getElemName(param)

        # Make sure the number of leading "p" matches the pointer count.
        pointercount = param.find('type').tail
        if pointercount:
            pointercount = pointercount.count('*')
        if pointercount:
            prefix = 'p' * pointercount
            if not param_name.startswith(prefix):
                self.record_error("Apparently incorrect pointer-related name prefix for",
                                  param_text, "- expected it to start with", prefix,
                                  elem=param)

    def check_type(self, name, info, category):
        """Check a type's XML data for consistency.

        Called from check."""

        elem = info.elem
        type_elts = [elt
                     for elt in elem.findall("member")
                     if getElemType(elt) == TYPEENUM]
        if category == 'struct' and type_elts:
            if len(type_elts) > 1:
                self.record_error(
                    "Have more than one member of type", TYPEENUM)
            else:
                type_elt = type_elts[0]
                val = type_elt.get('values')
                if val and val not in self.structure_types:
                    self.record_error("Unknown structure type constant", val)
        elif category == "bitmask":
            if 'Flags' in name:
                expected_require = name.replace('Flags', 'FlagBits')
                require = info.elem.get('require')
                if require is not None and expected_require != require:
                    self.record_error("Unexpected require attribute value:",
                                      "got", require,
                                      "but expected", expected_require)
        super().check_type(name, info, category)

    def check_extension(self, name, info):
        """Check an extension's XML data for consistency.

        Called from check."""
        elem = info.elem
        enums = elem.findall('./require/enum[@name]')

        # Get the way it's spelling in enum names
        ext_enum_name = EXTENSION_ENUM_NAME_SPELLING_CHANGE.get(
            name, name.upper())
        version_name = "{}_SPEC_VERSION".format(ext_enum_name)
        version_elem = findNamedElem(enums, version_name)
        if version_elem is None:
            self.record_error("Missing version enum", version_name)
        else:
            fn = get_extension_source(name)
            revisions = []
            with open(fn, 'r', encoding='utf-8') as fp:
                for line in fp:
                    line = line.rstrip()
                    match = REVISION_RE.match(line)
                    if match:
                        revisions.append(int(match.group('num')))
            ver_from_xml = version_elem.get('value')
            if revisions:
                ver_from_text = str(max(revisions))
                if ver_from_xml != ver_from_text:
                    self.record_error("Version enum mismatch: spec text indicates", ver_from_text,
                                      "but XML says", ver_from_xml)
            else:
                if ver_from_xml == '1':
                    self.record_warning(
                        "Cannot find version history in spec text - make sure it has lines starting exactly like '* Revision 1, ....'",
                        filename=fn)
                else:
                    self.record_warning("Cannot find version history in spec text, but XML reports a non-1 version number", ver_from_xml,
                                        " - make sure the spec text has lines starting exactly like '* Revision 1, ....'",
                                        filename=fn)

        name_define = "{}_EXTENSION_NAME".format(ext_enum_name)
        name_elem = findNamedElem(enums, name_define)
        if name_elem is None:
            self.record_error("Missing name enum", name_define)
        else:
            # Note: etree handles the XML entities here and turns &quot; back into "
            expected_name = '"{}"'.format(name)
            name_val = name_elem.get('value')
            if name_val != expected_name:
                self.record_error("Incorrect name enum: expected", expected_name,
                                  "got", name_val)

        super().check_extension(name, elem)


if __name__ == "__main__":

    ckr = Checker()
    ckr.check()

    if ckr.fail:
        sys.exit(1)
