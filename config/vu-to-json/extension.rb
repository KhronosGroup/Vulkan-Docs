# Copyright (c) 2016-2018 The Khronos Group Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

module Asciidoctor

class ValidUsageToJsonPreprocessorReader < PreprocessorReader
  def process_line line
    if line.start_with?( 'ifdef::VK_', 'ifndef::VK_', 'endif::VK_')
      # Turn extension ifdefs into list items for when we're processing VU later.
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
    # FIXME in Reader#peek_line suggests that this doesn't work, the new lines are simply discarded.
    # So we just run over the new lines and do the replacement again.
    new_lines = extension_preprocessor_reader.read_lines().flat_map do | line |
          
      # Track whether we're in a VU block or not
      if line.start_with?(".Valid Usage")
        in_validusage = :about_to_enter  # About to enter VU
      elsif in_validusage == :about_to_enter and line == '****'
        in_validusage = :inside   # Entered VU block
        extension_stack.each 
      elsif in_validusage == :inside and line == '****' 
        in_validusage = :outside   # Exited VU block
      end
      
      # Track extensions outside of the VU
      if in_validusage == :outside and line.start_with?( 'ifdef::VK_', 'ifndef::VK_') and line.end_with?( '[]')
        extension_stack.push line
      elsif in_validusage == :outside and line.start_with?( 'endif::VK_')
        extension_stack.pop
      end
      
      if in_validusage == :inside and line == '****' 
        # Write out the extension stack as bullets after this line
        returned_lines = [line]
        extension_stack.each do | extension |
          returned_lines << ('* ' + extension)
        end
        returned_lines
      elsif in_validusage == :inside and line.start_with?( 'ifdef::VK_', 'ifndef::VK_', 'endif::VK_') and line.end_with?('[]')
        # Turn extension ifdefs into list items for when we're processing VU later.
        ['* ' + line]
      elsif in_validusage == :outside and line.start_with?( 'ifdef::VK_', 'ifndef::VK_', 'endif::VK_') and line.end_with?('[]')
        # Remove the extension defines from the new lines, as we've dealt with them
        []
      elsif line.match(/\[\[(VUID-([^-]+)-[^\]]+)\]\]/)
        # Add all the VUIDs into an array to guarantee they're all caught later.
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

    # Need to find all valid usage blocks within a structure or function ref page section
    
    # Find all the open blocks
    (document.find_by context: :open).each do |openblock|
      # Filter out anything that's not a refpage
      if openblock.attributes['refpage']
        if openblock.attributes['type'] == 'structs' || openblock.attributes['type'] == 'protos'
          parent = openblock.attributes['refpage']
          # Find all the sidebars
          (openblock.find_by context: :sidebar).each do |sidebar|
            # Filter only the valid usage sidebars
            if sidebar.title == "Valid Usage" || sidebar.title == "Valid Usage (Implicit)"
              # There should be only one block - but just in case...
              sidebar.blocks.each do |list|
                extensions = []
                # Iterate through all the items in the block, tracking which extensions are enabled/disabled.
                list.blocks.each do |item|
                  if item.text.start_with?('ifdef::VK_')
                    extensions << '(' + item.text[('ifdef::'.length)..-3] + ')'                # Look for "ifdef" directives and add them to the list of extensions
                  elsif item.text.start_with?('ifndef::VK_')
                    extensions << '!(' + item.text[('ifndef::'.length)..-3] + ')'              # Ditto for "ifndef" directives
                  elsif item.text.start_with?('endif::VK_')
                    extensions.slice!(-1)                                                      # Remove the last element when encountering an endif
                  else
                    match = /<a id=\"(VUID-([^-]+)-[^"]+)\"[^>]*><\/a>(.*)/m.match(item.text) # Otherwise, look for the VUID.
                    if (match != nil)
                      vuid     = match[1]
                      parentid = match[2]
                      text     = match[3].gsub("\n", ' ')  # Have to forcibly remove newline characters; for some reason they're translated to the literally '\n' when converting to json.

                      # Check parentid from VUID matches the parent - warn if not
                      if parentid != parent
                        puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement VUID parent conflicts with parent ref page. Expected parent of '#{parent}' but VUID was '#{vuid}'."
                      end
                      
                      # Delete the vuid from the detected vuid list, so we know it's been extracted successfully
                      detected_vuid_list.delete(vuid)

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
                        puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement '#{entry}' is duplicated in the specification with VUID '#{vuid}'."
                      end
                      
                      # Add the entry
                      map['validation'][parent][entry_section] << entry
                      
                    else
                      puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement without a VUID found: "
                      puts item.text
                    end
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
        puts 'VU Extraction JSON Validator: WARNING - Validation of the json schema failed'
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
    exit! 0
  end
end
end
