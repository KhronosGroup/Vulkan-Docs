#!/usr/bin/python3
#
# Copyright (c) 2019 Collabora, Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author(s):    Ryan Pavlik <ryan.pavlik@collabora.com>
#
# Purpose:      This script checks some "business logic" in the XML registry.

import sys
from pathlib import Path

from check_spec_links import VulkanEntityDatabase as OrigEntityDatabase
from reg import Registry
from spec_tools.consistency_tools import XMLChecker
from spec_tools.util import getElemType
from vkconventions import VulkanConventions as APIConventions


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
            # the codes of the value are available for a command if-and-only-if
            # the key type is passed as an input.
            # "XrSystemId":  "XR_ERROR_SYSTEM_INVALID",
            # "XrFormFactor": ("XR_ERROR_FORM_FACTOR_UNSUPPORTED",
            #                  "XR_ERROR_FORM_FACTOR_UNAVAILABLE"),
            # "XrInstance": ("XR_ERROR_INSTANCE_LOST"),
            # "XrSession":
            #     ("XR_ERROR_SESSION_LOST", "XR_SESSION_LOSS_PENDING"),
            # "XrPosef":
            #     "XR_ERROR_POSE_INVALID",
            # "XrViewConfigurationType":
            #     "XR_ERROR_VIEW_CONFIGURATION_TYPE_UNSUPPORTED",
            # "XrEnvironmentBlendMode":
            #     "XR_ERROR_ENVIRONMENT_BLEND_MODE_UNSUPPORTED",
            # "XrCompositionLayerBaseHeader": ("XR_ERROR_LAYER_INVALID"),
            # "XrInteractionProfileSuggestedBinding":
            #     "XR_ERROR_BINDINGS_DUPLICATED",
            # "XrPath": "XR_ERROR_PATH_INVALID",
            # "XrTime": "XR_ERROR_TIME_INVALID"
        }
        forward_only = {
            # Like the above, but these are only valid in the
            # "type implies return code" direction
        }
        reverse_only = {
            # like the above, but these are only valid in the
            # "return code implies type or its descendant" direction
            # "XrSession": ("XR_ERROR_SESSION_RUNNING",
            #               "XR_ERROR_SESSION_NOT_RUNNING",
            #               "XR_ERROR_SESSION_NOT_READY",
            #               "XR_ERROR_SESSION_NOT_STOPPING",
            #               "XR_SESSION_NOT_FOCUSED",
            #               "XR_FRAME_DISCARDED"),
            # "XrReferenceSpaceType": "XR_SPACE_BOUNDS_UNAVAILABLE",
            # "XrPath": "XR_ERROR_PATH_UNSUPPORTED",
            # "XrDuration": "XR_TIMEOUT_EXPIRED"
        }

        # Some return codes are related in that only one of a set
        # may be returned by a command
        # (eg. XR_ERROR_SESSION_RUNNING and XR_ERROR_SESSION_NOT_RUNNING)
        self.exclusive_return_code_sets = (
            tuple()
            # set(("XR_ERROR_SESSION_NOT_RUNNING", "XR_ERROR_SESSION_RUNNING")),
        )

        conventions = APIConventions()
        db = EntityDatabase()

        self.extension_cmds = get_extension_commands(db.registry)
        self.return_codes = get_enum_value_names(db.registry, 'VkResult')
        self.structure_types = get_enum_value_names(db.registry, TYPEENUM)

        # Dict of entity name to a list of messages to suppress. (Exclude any context data and "Warning:"/"Error:")
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

        for exclusive_set in self.exclusive_return_code_sets:
            specified_exclusives = exclusive_set.intersection(codes)
            if len(specified_exclusives) > 1:
                self.record_error(
                    "Mutually-exclusive return codes specified:",
                    specified_exclusives)

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


ckr = Checker()
ckr.check()

if ckr.fail:
    sys.exit(1)
