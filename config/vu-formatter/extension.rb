# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vu_helpers') : (require_relative '../helpers/vu_helpers')

include ::Asciidoctor

module Asciidoctor

def parse_formatted_english_line(line)
  # Count what the nested level is
  level = line.split(' ')[0].count('*')
  raise 'Unexpected English-formatted line syntax (sublist level)' if level == 0
  raise 'Unexpected English-formatted line syntax (sublist syntax)' if line[level] != ' '

  return level, line[level+1..]
end

def parse_formatted_english(parent_item, nest_level, lines, start_index)
  list = List.new parent_item, :ulist

  current_index = start_index
  while current_index < lines.length
    level, content = parse_formatted_english_line(lines[current_index])

    # If this sublist is finished, return to parent
    if level < nest_level
      break
    end

    # If level is as expected, add it as an item in the current list
    if level == nest_level
      list_item = ListItem.new list, content
      list.items << list_item
      current_index += 1
      next
    end

    # Recursively create a sublist
    raise 'Unexpected formatting, encountered nesting level difference more than one' if level > nest_level + 1
    raise 'Internal error when parsing formatted English' if list.items.empty?
    current_index = parse_formatted_english(list.items[-1], nest_level + 1, lines, current_index)
  end

  parent_item.blocks << list
  return current_index
end

require 'json'
class VuFormatterTreeprocessor < Extensions::Treeprocessor
  def process document
    formatter, docattributes, error_found = spawn_vuformatter document.instance_variable_get(:@attributes)

    api = ''

    # Iterate through all blocks and process valid usage blocks
    # Use find_by so that sub-blocks that this script processes can be skipped
    document.find_by do |block|

      # Keep track of all attributes defined throughout the document, as Asciidoctor will not do this automatically.
      # See https://discuss.asciidoctor.org/asciidoctorj-and-document-attributes-tp5960p6525.html
      document.playback_attributes(block.attributes)

      # Track the parent block for each subsequent valid usage block
      if block.context == :open and block.attributes['refpage']
        api = block.attributes['refpage']
      end

      # Filter out anything that is not a refpage
      if block.context == :sidebar && (block.title == "Valid Usage" || block.title == "Valid Usage (Implicit)")

        # Iterate through all the VU lists in each block
        block.blocks.each do |list|

          # Play back list attributes
          document.playback_attributes(list.attributes)

          # Iterate through all the items in the block, tracking which extensions are enabled/disabled.
          items = []
          list.blocks.each do |item|

            # Attribute definitions split lists, so no need to play back attributes between list items

            item_text = item.instance_variable_get(:@text).clone

            # Remove the VUID from the vu, if any
            match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(item_text)

            vuid = nil
            text = item_text
            if !match.nil?
              vuid = match[1]
              text = match[2].strip()
            end

            # Remove workaround added by WorkaroundWhitespaceSwallowPreprocessor
            if text.start_with? 'WORKAROUND'
              text.gsub!('WORKAROUND', '')
            end

            if not is_codified_vu text
              # For now, codified VUs are identified with "codified-vu" for simplicity.  Eventually
              # this can be removed as codified VUs become commonplace.  Until then, make sure this
              # tag is not missed.
              if text.include? 'require('
                puts 'ERROR: Detected codified VU without the codified-vu tag.  Please start the VU with a line containing "codified-vu"'
                puts 'ERROR: Offending VU is:'
                puts text
              end

              items.append(item)
              next
            end

            # Get the attributes that may be used in the VUs as macro() values.  They are whatever
            # attribute was defined since the beginning of the document.
            current_attributes = document.instance_variable_get(:@attributes)
            current_attributes = current_attributes.reject { |attr| docattributes.include? attr }

            # Format the VU.  This parses and type checks the VU, so it can report failure.
            formatted, formattedEnglish, passed = format_vu(formatter, api, item.source_location, current_attributes, text)

            if passed == FormatResult::ELIMINATED
              # The VU was eliminated in this build
              next
            end

            if passed == FormatResult::FAILED
              error_found = true
            end

            # For now, show English by default, and let the original be visible by hovering over this:
            formatted.prepend("[vu-hover]#Show Original# +")

            # Stitch [[vuid]] back to the item, if any.
            if not vuid.nil?
              formatted.prepend("[[" + vuid + "]]")
            end

            formatted = formatted.join("\n")

            # Replace < and > with &lt; and &gt; respectively to avoid contractions.
            formatted.gsub!('<', '&lt;')
            formatted.gsub!('>', '&gt;')

            # Replace the item text
            item.text = formatted
            parse_formatted_english(item, 1, formattedEnglish, 0)
            items.append(item)
          end
          # Substitute the items of this VU list with whatever VU was left
          list.instance_variable_set(:@blocks, items)
        end
      end
    end

    terminate_vuformatter(formatter)

    if (error_found)
      exit! 1
    end
  end
end

# Workaround an asciidoctor behavior when parsing a list item in the following
# form:
#
#   * some text
#       more text
#         etc
#       etc
#
# In the above case, asciidoctor swallows the indentation of the block before
# `more text`, turning the returned text as:
#
#   some text
#   more text
#     etc
#   etc
#
# This is only an issue with VUs that don't have a VUID, as otherwise the first
# line of the codified VU would not be at the `*`, and so the indentation of
# the whole block is relatively correct.
#
# To fix this, a preprocessor extension simply turns the above VU into:
#
#   * WORKAROUNDsome text
#     WORKAROUND  more text
#     WORKAROUND    etc
#     WORKAROUND  etc
#
# The VuFormatterTreeprocessor extension removes the WORKAROUND to get back the
# original VU.
#
# Note: With the advent of the "codified-vu" tag in the first line, this should
# be unnecessary, but is kept for the eventual removal of that tag.
# Ultimately, when codified VUs are widespread enough, the VU block should stop
# being a list and just be empty-line-separated VUs that are processed in a
# pre-processor extension (like VUs _used_ to be before the #ifdef-in-VU
# changes).  That can be done as soon as there are no longer #ifdefs in VUs (as
# in, they have all been codified)
class WorkaroundWhitespaceSwallowPreprocessorReader < PreprocessorReader
  attr_reader :in_validusage
  attr_reader :work_around

  def initialize document, lines
    @in_validusage = :outside
    @work_around = -1
    super(document,lines)
  end

  def is_vu_without_vuid line
    # The line must start with '  *', and with a single asterisk (otherwise it's a nested list)
    if line.lstrip[0] != '*' or line.lstrip[1] == '*'
      return false
    end

    content = line.lstrip[1..-1].lstrip
    first_char = content[0]
    if first_char == '['
      return false
    end

    # Ignore legacy VUs
    if first_char != '#' and not is_codified_vu content
      return false
    end

    # Otherwise it's a codified VU that may need a work around
    return true
  end

  def process_line line
    if line.start_with?(".Valid Usage")
      @in_validusage = :about_to_enter
    elsif @in_validusage == :about_to_enter and line == '****'
      @in_validusage = :inside
    elsif @in_validusage == :inside and line == '****'
      @in_validusage = :outside
    end

    if @in_validusage == :inside and is_vu_without_vuid line
      # The first non whitespace character is '*'.  Find out where the
      # contents actually begin by skipping whitespace after that too.
      first_char = line.lstrip[1..-1].lstrip[0]
      @work_around = line.index first_char
    elsif line.lstrip[0] == '*'
      # Continue the workaround until the next list item
      @work_around = -1
    end

    # If workaround is in effect, prefix every line with the constant
    # WORKAROUND at the same indentation
    if @work_around >= 0
      # Note: need to mutate line, because asciidoctor does not correctly
      # handle the case where super is called on a new object!  There is a
      # FIXME in Reader#peek_line about this.
      line.insert(@work_around, 'WORKAROUND')
    end

    super(line)
  end
end

class WorkaroundWhitespaceSwallowPreprocessor < Extensions::Preprocessor
  def process document, reader
    reader = WorkaroundWhitespaceSwallowPreprocessorReader.new(document, reader.lines)
  end
end
end
