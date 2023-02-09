# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'
RUBY_ENGINE == 'opal' ? (require 'vu_helpers') : (require_relative '../helpers/vu_helpers')

include ::Asciidoctor

module Asciidoctor

def is_adoc_ifdef line
  line.start_with?( 'ifdef::VK_', 'ifdef::VKSC_' )
end

def is_adoc_ifndef line
  line.start_with?( 'ifndef::VK_', 'ifndef::VKSC_' )
end

def is_adoc_endif line
  line.start_with?( 'endif::VK_', 'endif::VKSC_' )
end

def is_adoc_begin_conditional line
  is_adoc_ifdef(line) or is_adoc_ifndef(line)
end

def is_adoc_conditional line
  is_adoc_begin_conditional(line) or is_adoc_endif(line)
end

class ValidUsageToJsonPreprocessorReader < PreprocessorReader
  def process_line line
    if is_adoc_conditional(line)
      # Turn extension ifdefs into list items for when we are processing VU later.
      return super('* ' + line)
    else
      return super(line)
    end
  end
end

# Preprocessor hook to iterate over ifdefs to prevent them from affecting asciidoctor's processing.
class ValidUsageToJsonPreprocessor < Extensions::Preprocessor

  def process document, reader
    # Create a new reader to return, which handles turning the extension ifdefs into something else.
    extension_preprocessor_reader = ValidUsageToJsonPreprocessorReader.new(document, reader.lines)

    detected_vuid_list = []
    extension_stack = []
    in_validusage = :outside

    # Despite replacing lines in the overridden preprocessor reader, a
    # FIXME in Reader#peek_line suggests that this does not work, the new lines are simply discarded.
    # So we just run over the new lines and do the replacement again.
    new_lines = extension_preprocessor_reader.read_lines().flat_map do | line |

      # Track whether we are in a VU block or not
      if line.start_with?(".Valid Usage")
        in_validusage = :about_to_enter  # About to enter VU
      elsif in_validusage == :about_to_enter and line == '****'
        in_validusage = :inside   # Entered VU block
        extension_stack.each
      elsif in_validusage == :inside and line == '****'
        in_validusage = :outside   # Exited VU block
      end

      # Track extensions outside of the VU
      if in_validusage == :outside and is_adoc_begin_conditional(line) and line.end_with?( '[]')
        extension_stack.push line
      elsif in_validusage == :outside and is_adoc_endif(line)
        extension_stack.pop
      end

      if in_validusage == :inside and line == '****'
        # Write out the extension stack as bullets after this line
        returned_lines = [line]
        extension_stack.each do | extension |
          returned_lines << ('* ' + extension)
          # Add extra blank line to avoid this item absorbing any markup such as attributes on the next line
          returned_lines << ''
        end
        returned_lines
      elsif in_validusage == :inside and is_adoc_conditional(line) and line.end_with?('[]')
        # Turn extension ifdefs into list items for when we are processing VU later.
        ['* ' + line]
      elsif in_validusage == :outside and is_adoc_conditional(line) and line.end_with?('[]')
        # Remove the extension defines from the new lines, as we have dealt with them
        []
      elsif line.match(/\[\[(VUID-([^-]+)-[^\]]+)\]\]/)
        # Add all the VUIDs into an array to guarantee they are all caught later.
        detected_vuid_list << line.match(/(VUID-([^-]+)-[^\]]+)/)[0]
        [line]
      else
        [line]
      end
    end

    # Stash the detected vuids into a document attribute
    document.set_attribute('detected_vuid_list', detected_vuid_list.join("\n"))

    # Return a new reader after preprocessing
    Reader.new(new_lines)
  end
end

def replace_macro_in_codified_vu(text, attrib, value)
  # This function is identical to convertMacrosToVuLanguage followed by
  # expandVuMacros in vuAST.py.
  vuValue = value.clone
  vuValue.gsub!('pname:', '')
  vuValue.gsub!('->', '.')

  text.gsub!('macro(' + attrib + ')', vuValue)
end

def replace_attribs(text, attribs)
  attribs.each do |attrib, value|
    replacement_str = '\{' + attrib + '\}'
    replacement_regex = Regexp.new(replacement_str, Regexp::IGNORECASE)
    text.gsub!(replacement_regex, value)
  end
end

require 'json'
class ValidUsageToJsonTreeprocessor < Extensions::Treeprocessor
  def process document
    map = {}

    # Get the global vuid list
    detected_vuid_list = document.attr('detected_vuid_list').split("\n")

    map['version info'] = {
      'schema version' => 2,
      'api version' => document.attr('revnumber'),
      'comment' => document.attr('revremark'),
      'date' => document.attr('revdate')
    }

    map['validation'] = {}

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
          parent = openblock.attributes['refpage']
          accumulate_attribs(current_attributes, [Asciidoctor::Document::AttributeEntry.new('refpage', parent)])
          # Find all the sidebars
          (openblock.find_by context: :sidebar).each do |sidebar|
            accumulate_attribs(current_attributes, sidebar.attributes[:attribute_entries])
            # Filter only the valid usage sidebars
            if sidebar.title == "Valid Usage" || sidebar.title == "Valid Usage (Implicit)"
              extensions = []
              # There should be only one block - but just in case...
              sidebar.blocks.each do |list|
                # Iterate through all the items in the block, tracking which extensions are enabled/disabled.
                accumulate_attribs(current_attributes, list.attributes[:attribute_entries])

                list.blocks.each do |item|
                  accumulate_attribs(current_attributes, item.attributes[:attribute_entries])

                  if is_adoc_ifdef(item.text)
                    extensions << '(' + item.text[('ifdef::'.length)..-3] + ')'                # Look for "ifdef" directives and add them to the list of extensions
                  elsif is_adoc_ifndef(item.text)
                    extensions << '!(' + item.text[('ifndef::'.length)..-3] + ')'              # Ditto for "ifndef" directives
                  elsif is_adoc_endif(item.text)
                    extensions.slice!(-1)                                                      # Remove the last element when encountering an endif
                  else
                    unconverted_text = item.instance_variable_get(:@text).clone

                    # Look up the vuid in the text of the anchor
                    match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(unconverted_text)

                    if (match == nil)
                      puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement without a VUID found: "
                      puts unconverted_text
                      next
                    end

                    vuid = match[1]
                    unconverted = match[2].lstrip()

                    # Delete the vuid from the detected vuid list, so we know it is been extracted successfully
                    detected_vuid_list.delete(vuid)

                    replace_attribs(vuid, current_attributes)

                    # For codified VUs, output the text in source format, only with attributes replaced.
                    if is_codified_vu(unconverted)
                      current_attributes.each do |attrib, value|
                        replace_macro_in_codified_vu(unconverted, attrib, value)
                      end
                      text = unconverted
                    else
                      item_text = item.text.clone

                      # Replace any attributes specified in the doc (e.g. stageMask)
                      replace_attribs(item_text, current_attributes)

                      match = nil
                      if item.text == item_text
                        # The VUID will have been converted to a href in the general case, so find that
                        match = /<a id=\"(VUID-[^"]+)\"[^>]*><\/a>(.*)/m.match(item_text)
                      else
                        # If we are doing manual attribute replacement, have to find the text of the anchor
                        match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(item_text) # Otherwise, look for the VUID.
                      end

                      # Have to forcibly remove newline characters, otherwise
                      # they are translated to the literal '\n' when converting
                      # to json as json doesn't support multi-line strings.
                      text = match[2].gsub("\n", ' ')
                    end

                    # Generate the table entry
                    entry = {'vuid' => vuid, 'text' => text}

                    # Initialize the database if necessary
                    if map['validation'][parent] == nil
                      map['validation'][parent] = {}
                    end

                    # Figure out the name of the section the entry will be added in
                    if extensions == []
                      entry_section = 'core'
                    else
                      entry_section = extensions.join('+')
                    end

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
              end
            end
          end

        end
      end
    end

    # Print out a list of VUIDs that were not extracted
    if detected_vuid_list.length != 0
      error_found = true
      puts 'VU Extraction Treeprocessor: ERROR - Extraction failure'
      puts
      puts 'Some VUIDs were not successfully extracted from the specification.'
      puts 'This is usually down to them appearing outside of a refpage (open)'
      puts 'block; try checking where they are included.'
      puts 'The following VUIDs were not extracted:'
      detected_vuid_list.each do |vuid|
        puts "\t * " + vuid
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
