# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

module Asciidoctor

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
    error_found = false


      
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
            
            if (match != nil)
              vuid     = match[1]
              text     = match[2]

              # Remove newlines present in the asciidoctor source
              text.gsub!("\n", ' ')

              # Append text for all the subbullets
              text += item.content

              # Strip any excess leading/trailing whitespace
              text.strip!

              # Generate the table entry
              entry = {'vuid' => vuid, 'text' => text, 'page' => 'vkspec' }

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
              puts item.text
            end
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

    if (error_found)
      exit! 1
    end
    exit! 0
  end
end
end
