# Copyright 2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vu_helpers') : (require_relative '../helpers/vu_helpers')

include ::Asciidoctor

module Asciidoctor

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
  passed = false
  while not formatter.eof? do
    line = formatter.gets
    if line.start_with? 'FORMAT-VU'
      passed = line.rstrip() == 'FORMAT-VU-SUCCESS'
      break
    end
    formattedText.append(line.rstrip())
  end

  # Output messages, if any, and report failure if that's the case.
  puts messages
  if not passed
    puts 'ERROR: Build failure with codified VU (see previous messages) (attributes are: ' + attribs.to_s + ')'
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

    # Need to find all valid usage blocks within a structure or function ref page section
    # This is a list of all refpage types that may contain VUs
    vu_refpage_types = [
            'builtins',
            'funcpointers',
            'protos',
            'spirv',
            'structs',
        ]

    # Keep track of all attributes defined before or inside .Valid Usage
    # sidebars.  Note that attributes set elsewhere may be lost; this is a
    # limitation of asciidoctor.  See
    # https://discuss.asciidoctor.org/asciidoctorj-and-document-attributes-tp5960p6525.html
    current_attributes = {}

    # Find all the open blocks
    (document.find_by context: :open).each do |openblock|
      # Filter out anything that is not a refpage
      if openblock.attributes['refpage']
        if vu_refpage_types.include? openblock.attributes['type']
          api = openblock.attributes['refpage']
          accumulate_attribs(current_attributes, [Asciidoctor::Document::AttributeEntry.new('refpage', api)])
          # Find all the sidebars
          (openblock.find_by context: :sidebar).each do |sidebar|
            accumulate_attribs(current_attributes, sidebar.attributes[:attribute_entries])
            # Filter only the valid usage sidebars
            if sidebar.title == "Valid Usage" || sidebar.title == "Valid Usage (Implicit)"
              extensions = []
              # There should be only one block - but just in case...
              sidebar.blocks.each do |list|
                # Iterate through all the items in the block

                accumulate_attribs(current_attributes, list.attributes[:attribute_entries])

                list.blocks.each do |item|
                  accumulate_attribs(current_attributes, item.attributes[:attribute_entries])
                  item_text = item.instance_variable_get(:@text).clone

                  # Remove the VUID from the vu, if any
                  match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(item_text)

                  vuid = nil
                  text = item_text
                  if !match.nil?
                    vuid = match[1]
                    text = match[2].strip()
                  end

                  if not is_codified_vu(text)
                    next
                  end

                  # Format the VU.  This parses and type checks the VU, so it can report failure.
                  formatted, passed = format_vu(formatter, api, item.source_location, current_attributes, text)

                  if not passed
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
                end
              end
            end
          end
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
end
