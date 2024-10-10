# Copyright 2016-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vu_helpers') : (require_relative '../helpers/vu_helpers')

include ::Asciidoctor

module Asciidoctor

def remove_markup(text)
  # Undo the mark up added for the generated text.  Eventually and ideally,
  # codified VUs are written as-is in validusage.json, in which case VVL would
  # generate text/code as it sees fit, and this step becomes unnecessary.

  # Replace [style]##...## with ..
  text.gsub!(/\[[^\]]*\]##([^#]*)##/, '\1')
  # Replace <<link,..>> with ..
  text.gsub!(/<<[^,]*,([^>]*)>>/, '\1')

  text.gsub!('ename:', '')
  text.gsub!('sname:', '')
  text.gsub!('fname:', '')
  text.gsub!('dname:', '')
  text.gsub!('tname:', '')
  text.gsub!('elink:', '')
  text.gsub!('slink:', '')
  text.gsub!('flink:', '')
  text.gsub!('dlink:', '')
  text.gsub!('tlink:', '')
  text.gsub!('pname:', '')
  text.gsub!('must:', 'must')
  text.gsub!('&lpar;', '(')
  text.gsub!('&rpar;', ')')
  text.gsub!('&lbrack;', '[')
  text.gsub!('&rbrack;', ']')
end

require 'json'
class ValidUsageToJsonTreeprocessor < Extensions::Treeprocessor
  def process document
    map = {}

    map['version info'] = {
      'schema version' => 2,
      'api version' => document.attr('revnumber'),
      'comment' => document.attr('revremark'),
      'date' => document.attr('revdate')
    }

    map['validation'] = {}

    parent = ''
    formatter, docattributes, error_found = spawn_vuformatter document.instance_variable_get(:@attributes)

    # Iterate through all blocks and process valid usage blocks
    # Use find_by so that sub-blocks that this script processes can be skipped
    document.find_by do |block|

      # Keep track of all attributes defined throughout the document, as Asciidoctor will not do this automatically.
      # See https://discuss.asciidoctor.org/asciidoctorj-and-document-attributes-tp5960p6525.html
      document.playback_attributes(block.attributes)

      # Track the parent block for each subsequent valid usage block
      if block.context == :open and block.attributes['refpage']
        parent = block.attributes['refpage']
      end

      # Filter out anything that is not a refpage
      if block.context == :sidebar && (block.title == "Valid Usage" || block.title == "Valid Usage (Implicit)")

        # Iterate through all the VU lists in each block
        block.blocks.each do |list|

          # Play back list attributes
          document.playback_attributes(list.attributes)

          # Iterate through all the items in the block, tracking which extensions are enabled/disabled.
          list.blocks.each do |item|

            # Attribute definitions split lists, so no need to play back attributes between list items

            # Look for converted anchors
            match = /<a id=\"(VUID-[^"]+)\"[^>]*><\/a>(.*)/m.match(item.text)

            if (match == nil)
              puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement without a VUID found: "
              puts item.instance_variable_get(:@text)
              next
            end

            vuid = match[1]
            text = match[2]

            # For codified VUs, output the text in source format, only with attributes replaced.
            # For them, the unconverted text is used.
            unconverted_text = item.instance_variable_get(:@text)
            match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(unconverted_text)
            unconverted = match[2].lstrip()

            if is_codified_vu(unconverted)
              # Get the attributes that may be used in the VUs as macro() values.  They are whatever
              # attribute was defined since the beginning of the document.
              current_attributes = document.instance_variable_get(:@attributes)
              current_attributes = current_attributes.reject { |attr| docattributes.include? attr }

              # Format the VU.  Assuming build is already green, this should pass
              formatted, formattedEnglish, passed = format_vu(formatter, parent, item.source_location, current_attributes, unconverted)
              if passed == FormatResult::ELIMINATED
                puts "ERROR: validusage should be run on a complete build of the spec, but a VU was eliminated in this build"
                puts 'ERROR: Offending VU is:'
                puts unconverted
                error_found = true
                next
              end
              if passed == FormatResult::FAILED
                puts "ERROR: validusage failed to verify VU.  Make sure the spec build passes before extracing VUs"
                puts 'ERROR: Offending VU is:'
                puts unconverted
                error_found = true
              end

              # For now, the English translation is passed to VVL.  Eventually,
              # it'll be best if the codified version is passed directly (after
              # replacing macros) and VVL can generate English or formatted
              # code as it sees fit.  It could also extract other information,
              # such as the list of predicates so it can automatically generate
              # helpful descriptions of them.
              text = formattedEnglish.join("\n")
              remove_markup text
            else
              # Remove newlines present in the asciidoctor source
              text.gsub!("\n", ' ')

              # Append text for all the subbullets
              text += item.content

              # Strip any excess leading/trailing whitespace
              text.strip!
            end

            # Generate the table entry
            entry = {'vuid' => vuid, 'text' => text, 'page' => 'vkspec'}

            # Initialize the database if necessary
            if map['validation'][parent] == nil
              map['validation'][parent] = {}
            end

            # For legacy schema reasons, put everything in "core" entry section
            entry_section = 'core'

            # Initialize the entry section if necessary
            if map['validation'][parent][entry_section] == nil
              map['validation'][parent][entry_section] = []
            end

            # Check for duplicate entries
            if map['validation'][parent][entry_section].include? entry
              error_found = true
              puts "VU Extraction Treeprocessor: ERROR - Valid Usage statement '#{entry}' is duplicated in the specification with VUID '#{vuid}'."
            end

            # Add the entry
            map['validation'][parent][entry_section] << entry
          end
        end
        # This block's sub blocks have been handled through iteration, so return true to avoid the main loop re-processing them
        true
      else
        # This block was not what we were looking for, so let asciidoctor continue iterating through its sub blocks
        false
      end
    end


    # Generate the json
    json = JSON.pretty_generate(map)
    outfile = document.attr('json_output')

    # Verify the json against the schema, if the required gem is installed
    begin
      require 'json-schema'

      # Read the schema in and validate against it
      schema = IO.read(File.join(File.dirname(__FILE__), 'vu_schema.json'))
      errors = JSON::Validator.fully_validate(schema, json, :errors_as_objects => true)

      # Output errors if there were any
      if errors != []
        error_found = true
        puts 'VU Extraction JSON Validator: ERROR - Validation of the json schema failed'
        puts
        puts 'It is likely that there is an invalid or malformed entry in the specification text,'
        puts 'see below error messages for details, and use their VUIDs and text to correlate them to their location in the specification.'
        puts

        errors.each do |error|
          puts error.to_s
        end
      end
    rescue LoadError
      puts 'VU Extraction JSON Validator: WARNING - "json-schema" gem missing - skipping verification of json output'
      # error handling code here
    end

    # Write the file and exit - no further processing required.
    IO.write(outfile, json)

    if error_found
      exit! 1
    end
    exit! 0
  end
end
end
