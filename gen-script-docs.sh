#!/bin/sh
# Copyright 2019-2021 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Generate documentation for the python scripts in this repo, using pdoc3:
# https://pdoc3.github.io/pdoc/
#
# Output is under out/python-docs

set -e

# Pipe in some paths. We'll convert them to module names and document them.
pathsToDocs() {
    grep -v "test_" | \
    grep -v "__init__.py" | \
    sed -e 's/[.]py//' -e 's:/:.:g' | \
    xargs --verbose pdoc3 --html --force --output-dir $1
}

# Main body of script
(
    cd $(dirname $0)
    # Needed to complete the build - can't import genRef.py without it.
    make gen/api.py

    SPECDIR=$(pwd)
    OUTDIR=$(pwd)/out/python-docs
    INDEX=$OUTDIR/index.html
    mkdir -p $OUTDIR
    cp scripts/__init__.py.docs scripts/__init__.py
    export PYTHONPATH=${SPECDIR}/scripts
    (
        # # scripts under specification
        cd $SPECDIR/scripts
        ls *.py

        # Generate the index files
        # echo "scripts"
        echo "scripts.spec_tools"

    ) | pathsToDocs $OUTDIR

    # Generate a simple index file, since generating one with pdoc3 chokes on the Retired directory.
    echo "<html><body><h1>Python modules</h2><ul>" > $INDEX
    (
        cd $SPECDIR/scripts
        ls *.py
    ) | while read -r fn; do
        MODNAME=$(echo $fn | sed -r  's/([a-zA-Z_]+)([.]py)?/\1/')
        if [ -f $OUTDIR/$MODNAME.html ]; then
            # Only make non-dead links
            echo "<li><a href=$MODNAME.html>$MODNAME</a></li>" >> $INDEX
        fi
    done
    echo "<li><a href=spec_tools/index.html>spec_tools</a></li>" >> $INDEX
    echo "</ul></body></html>" >> $INDEX

    # Move index files to a more useful place
    rm -rf $OUTDIR/spec_tools
    mv $OUTDIR/scripts/spec_tools $OUTDIR/spec_tools
    # delete duplicate generated files
    rm -rf $OUTDIR/scripts

    rm -f scripts/__init__.py
)
