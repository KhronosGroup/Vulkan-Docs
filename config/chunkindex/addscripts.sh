#!/bin/sh
# Copyright 2020-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Replace marker comments in asciidoctor-generated HTML with JavaScript
# and HTML supporting the searchbox.
#
# The marker comments are inserted by config/loadable_html/extension.rb,
# and are a stable place to add these comments, unlike the previous
# method of using 'patch'. That could fail when moving to new
# asciidoctor versions and style files. This can still fail, but should
# be more robust.
#
# Usage: addscripts.sh input-file output-file

# Find path to the script, which is also the patch to the replacements
path=`dirname $0`

input=$1
output=$2
test -f $input || (echo "No input file $1" ; exit 1)

# Replace the first marker comment with text in addscript.jsmarker
# Replace the second marker comment with text in addscript.searchboxmarker

cp $input $output
sed -i -e '/<\!--ChunkedSearchJSMarker-->/r '"$path/addscript.jsmarker" \
       -e '/<\!--ChunkedSearchboxMarker-->/r '"$path/addscript.searchboxmarker" \
       $output
