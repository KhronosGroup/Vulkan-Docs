# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

module Asciidoctor

def accumulate_attribs(current_attributes, new_attributes)
  if new_attributes.nil?
    return
  end

  new_attributes.each do |attr|
    current_attributes[attr.name] = attr.value
  end
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

                last_match = nil
                list.blocks.each do |item|
                  accumulate_attribs(current_attributes, item.attributes[:attribute_entries])

                  item_text = item.text.clone

                  # Replace any attributes specified in the doc (e.g. stageMask)
                  current_attributes.each do |attrib, value|
                    replacement_str = '\{' + attrib + '\}'
                    replacement_regex = Regexp.new(replacement_str, Regexp::IGNORECASE)
                    item_text.gsub!(replacement_regex, value)
                  end

                  match = nil
                  if item.text == item_text
                    # The VUID will have been converted to a href in the general case, so find that
                    match = /<a id=\"(VUID-[^"]+)\"[^>]*><\/a>(.*)/m.match(item_text)
                  else
                    # If we are doing manual attribute replacement, have to find the text of the anchor
                    match = /\[\[(VUID-[^\]]+)\]\](.*)/m.match(item_text) # Otherwise, look for the VUID.
                  end

                  if (match != nil)
                    last_match = match
                    vuid     = match[1]
                    text     = match[2]

                    # Remove newlines present in the asciidoctor source
                    text.gsub!("\n", ' ')

                    # Append text for all the subbullets
                    text += item.content

                    # Generate the table entry
                    entry = {'vuid' => vuid, 'text' => text}

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
                  else
                    puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement without a VUID found: "
                    puts item_text
                  end
                end
              end
            end
          end

        end
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

    if (error_found)
      exit! 1
    end
    exit! 0
  end
end
end
