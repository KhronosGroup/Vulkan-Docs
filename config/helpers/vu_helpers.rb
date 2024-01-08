# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

def is_codified_vu(vu)
  # This function is identical to isCodifiedVU in vuAST.py. Because the vu is
  # extracted from the asciidoctor list item however, it doesn't need to
  # preprocess it the same way (stripping '*', etc).
  vu.split("\n").each do |line|
    if line.start_with? '#'
      next
    end
    isIf = line.start_with? 'if '
    isFor = line.start_with? 'for '
    isWhile = line.start_with? 'while '
    isRequire = line.start_with? 'require('

    # Assignments are in the form `a.b.c = ...`
    isAssign = !line[/\A[a-zA-Z0-9_.]+\s*=/].nil?

    return isIf || isFor || isWhile || isRequire || isAssign
  end
  return false
end
