# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vu_helpers') : (require_relative '../helpers/vu_helpers')

include ::Asciidoctor

module Asciidoctor

class FormatResult
  PASSED = 0
  FAILED = 1
  ELIMINATED = 2
end

def get_build_info(attributes)
  docattributes = Set.new attributes.keys
  # Versions are those in the form of VK_VERSION_X_Y
  versions = docattributes.select { |attr| attr.start_with? "vk_version_" }
  # Extensions are in the form of VK_...., excluding the versions
  extensions = docattributes.select { |attr| attr.start_with? "vk_" and !versions.any? attr }

  return versions, extensions, docattributes
end

def send_build_versions(formatter, versions, extensions)
  formatter.puts 'VERSIONS'
  formatter.puts versions.join(' ')
  formatter.puts extensions.join(' ')
  formatter.puts 'VERSIONS-END'
  formatter.flush

  passed = false
  while not formatter.eof? do
    line = formatter.gets
    if line.start_with? 'VERSIONS'
      # Failure is not expected, but checking just in case.
      if line.strip() == 'VERSIONS-SUCCESS'
        passed = true
      end
      break
    end
    # If there are any error messages, output them
    puts line
  end

  return passed
end

def format_vu(formatter, api, location, attribs, text)
  # See vupreprocessor.py for the format of the message
  formatter.puts 'FORMAT-VU'
  formatter.puts api
  if location.nil?
    formatter.puts '<Need new asciidoctor version>'
    formatter.puts 0
  else
    formatter.puts location.file
    formatter.puts location.lineno
  end
  formatter.puts attribs.keys.zip(attribs.values).join('$')
  formatter.puts text
  formatter.puts 'FORMAT-VU-END'
  formatter.flush

  # Read back the results from the formatter
  messages = []
  formattedText = []

  # Get the error messages, if any
  while not formatter.eof? do
    line = formatter.gets
    if line.rstrip() == 'FORMAT-VU'
      break
    end
    messages.append(line.rstrip())
  end

  # Get the formatted text
  passed = FormatResult::FAILED
  while not formatter.eof? do
    line = formatter.gets
    if line.start_with? 'FORMAT-VU'
      if line.strip() == 'FORMAT-VU-SUCCESS'
        passed = FormatResult::PASSED
      elsif line.strip() == 'FORMAT-VU-ELIMINATED'
        passed = FormatResult::ELIMINATED
      end
      break
    end
    formattedText.append(line.rstrip())
  end

  # Output messages, if any, and report failure if that's the case.
  puts messages
  if passed == FormatResult::FAILED
    puts 'ERROR: Build failure with codified VU (see previous messages) (attributes are: ' + attribs.to_s + ')'
    puts 'ERROR: NOTE: asciidoctor does not track include files. If VU is in included file, source file location will be the parent file.'
    puts 'ERROR: NOTE: asciidoctor line info is not always accurate.  Offending VU is:'
    puts text
  end

  return formattedText, passed
end

require 'json'
class VuFormatterTreeprocessor < Extensions::Treeprocessor
  def process document
    # Create a python process as a service to convert VUs.  This avoids
    # creating a process for every VU, parsing the xml etc.
    vupreprocessor = File.expand_path(File.join(__dir__, '..', '..', 'scripts', 'vupreprocessor.py'))
    formatter = IO.popen(['python3', vupreprocessor], 'r+', :err=>[:child, :out])

    error_found = false

    # Preprocess the document attributes to extract the versions and extensions that are being
    # built.  Note that this information can be found in the document attributes (placed in
    # specattribs.adoc, which is included first thing in vkspec.adoc)
    #
    # Additionally, to avoid unnecessarily passing a lot of pre-specified attributes that won't be
    # of interest to codified VUs, whatever attribute is already defined at the document level will
    # be skipped when passing attributes to the vu formatter.
    versions, extensions, docattributes = get_build_info document.instance_variable_get(:@attributes)

    if !send_build_versions(formatter, versions, extensions)
      error_found = true
    end

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
              items.append(item)
              next
            end

            # Get the attributes that may be used in the VUs as macro() values.  They are whatever
            # attribute was defined since the beginning of the document.
            current_attributes = document.instance_variable_get(:@attributes)
            current_attributes = current_attributes.reject { |attr| docattributes.include? attr }

            # Format the VU.  This parses and type checks the VU, so it can report failure.
            formatted, passed = format_vu(formatter, api, item.source_location, current_attributes, text)

            if passed == FormatResult::ELIMINATED
              # The VU was eliminated in this build
              next
            end

            if passed == FormatResult::FAILED
              error_found = true
            end

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
            items.append(item)
          end
          # Substitute the items of this VU list with whatever VU was left
          list.instance_variable_set(:@blocks, items)
        end
      end
    end

    # Tell formatter to quit
    formatter.puts 'EXIT'
    formatter.close()

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
