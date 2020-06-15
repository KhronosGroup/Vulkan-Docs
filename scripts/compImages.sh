#!/bin/bash
#
# Copyright (c) 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# compareImages - compare all asciidoctor images in two branches
# Usage: compareImages branch1 branch2

# Where to put temporary files
compare=compare

branch1=$1
branch2=$2

echo "Preparing test tree under compare/"
rm -rf $compare

echo "Gathering images under compare/$1 compare/$2"
if git checkout $branch1 ; then
    img1=$compare/$branch1
    files1=$compare/$branch1-files
    mkdir -p $img1
    cp images/*.svg $img1
    (cd $img1 ; ls) > $files1
else
    echo "Can't switch to branch $branch1"
    rm -rf $compare
    exit 1
fi

if git checkout $branch2 ; then
    img2=$compare/$branch2
    files2=$compare/$branch2-files
    mkdir -p $img2
    cp images/*.svg $img2
    (cd $img2 ; ls) > $files2
else
    echo "Can't switch to branch $branch2"
    rm -rf $compare
    exit 1
fi

srcfile=compare/compImages.adoc

# Boilerplate header
echo "= Image Comparison of Vulkan images in $branch1 $branch2
:data-uri:
:icons: font
include::../config/attribs.txt[]
" > $srcfile


# Files common to both branches
echo "== Images Common to Both Branches
" >> $srcfile

# Identical images
identical=()

# Where to generate comparison images
compdir=$compare/compare
mkdir -p $compdir

for file in `comm -12 $files1 $files2` ; do
    echo "Comparing $file"
    if diff -q $img1/$file $img2/$file > /dev/null ; then
        identical+=( $file )
        # Files are identical
    else
        # sum1=`sum $img1/$file | awk '{print $1}'`
        # sum2=`sum $img2/$file | awk '{print $1}'`
        #
        # if test $sum1 -eq $sum2 ; then

        # Generate comparison image
        compfile="$compdir/$file"
        compare $img1/$file $img2/$file $compfile

        echo "=== $file

image::$branch1/$file[title=\"$file in $branch1\",align=\"center\",opts=\"inline\"]

image::$branch2/$file[title=\"$file in $branch2\",align=\"center\",opts=\"inline\"]

image::compare/$file[title=\"Comparison of branches\",align=\"center\",opts=\"inline\"]

<<<

" >> $srcfile

    fi
done


# Identical files
echo "== Identical images
" >> $srcfile

for file in ${identical[@]} ; do
    echo "  * $file" >> $srcfile
done
echo >> $srcfile


# Files only in first branch
echo "== Images only in $branch1
" >> $srcfile

for file in `comm -23 $files1 $files2` ; do
    echo "  * $file" >> $srcfile
done
echo >> $srcfile


# Files only in second branch
echo "== Images only in $branch2
" >> $srcfile

for file in `comm -13 $files1 $files2` ; do
    echo "  * $file" >> $srcfile
done
echo >> $srcfile

outfile=$compare/`basename $srcfile .adoc`.pdf
echo "Generating $outfile from $srcfile"
asciidoctor -b pdf -r asciidoctor-pdf -o $outfile $srcfile
