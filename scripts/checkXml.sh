#!/bin/sh -e
#
# Copyright 2019-2026 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
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

# checkXml.sh - Check the integrity of the RELAX-NG Compact schema,
# then validate the registry XML against it. For full functionality on
# Debian and friends, first install the packages as follows:
#
#   sudo apt install trang jing libxml2-utils xmlstarlet
#
# Usage: checkXml.sh
#
# Set FAIL_IF_COULD_NOT_VALIDATE=true before execution if you do not
# want a non-zero error code if no XML validators were found.

FAIL_IF_COULD_NOT_VALIDATE=${false:-$FAIL_IF_COULD_NOT_VALIDATE}

XML=xml/vk.xml
RNC=xml/registry.rnc
RNG=xml/registry.rng
REGEN_RNC=xml/regenerated.rnc

if which trang > /dev/null; then
    HAVE_TRANG=true
else
    HAVE_TRANG=false
fi

VALIDATED=false

doJing() {
    echo
    echo "Validating from rnc with jing"
    jing -c $RNC $XML 2>&1
    VALIDATED=true
}

doXmllint() {
    echo
    echo "Validating from rng with xmllint"
    #xmllint --debug $XML > registry/xml-debug.txt
    xmllint --noout --relaxng $RNG $XML 2>&1
    VALIDATED=true
}

doXmlStarlet() {
    echo
    echo "Validating from rng with xml starlet"
    xmlstarlet val --err --stop --relaxng $RNG $XML 2>&1
    VALIDATED=true
}

if $HAVE_TRANG; then
    echo
    echo "Converting $RNC to $RNG"
    trang $RNC $RNG
    echo "Converting $RNG back into $REGEN_RNC (formatted, but with some missing blank lines)"
    trang -o indent=4 $RNG $REGEN_RNC
    # Remove trailing whitespace from regenerated RNC
    sed -i.backup 's/ *$//' $REGEN_RNC
else
    echo "Recommend installing 'trang' for schema syntax checking and rnc <-> rng conversions."
fi

if which jing >/dev/null; then
    doJing
else
    echo "Recommend installing 'jing' for useful error messages in xml validation."
fi

if $HAVE_TRANG; then
    # Need trang to convert rnc->rng well.
    if which xmllint >/dev/null; then
        doXmllint
    fi
    if which xmlstarlet >/dev/null; then
        doXmlStarlet
    fi
fi

if ! $VALIDATED; then
    echo "No validators were found: looked for jing, xmllint (in package libxml2-utils), and xmlstarlet"
    if ! $HAVE_TRANG; then
        echo "'trang' is needed to run xmllint and xmlstarlet, while jing and trang are related projects"
        echo "They are in different packages on Debian, but might be in the same package on other platforms."
    fi
    echo
    if $FAIL_IF_COULD_NOT_VALIDATE; then
        echo "Exiting with failure."
        exit 1
    fi

    echo "Due to FAIL_IF_COULD_NOT_VALIDATE=false,"
    echo "skipping validation instead of exiting with failure."
    echo "REGISTRY XML WAS NOT CHECKED AGAINST SCHEMA!"
    exit 0
fi

echo
echo "XML validation complete with at least one tool."
