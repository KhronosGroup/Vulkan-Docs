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

    # Despite replacing lines in the overridden preprocessor reader, a
    # FIXME in Reader#peek_line suggests that this doesn't work, the new lines are simply discarded.
    # So we just run over the new lines and do the replacement again.
    new_lines = extension_preprocessor_reader.read_lines().map do | line |
      if line.start_with?( 'ifdef::VK_', 'ifndef::VK_', 'endif::VK_')
        # Turn extension ifdefs into list items for when we're processing VU later.
        '* ' + line
      elsif line.match(/\[\[(VUID-([^-]+)-[^\]]+)\]\]/)
        # Add all the VUIDs into an array to guarantee they're all caught later.
        detected_vuid_list << line.match(/(VUID-([^-]+)-[^\]]+)/)[0]
        line
      else
        line
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

    # Find all the sidebars
    (document.find_by context: :sidebar).each do |sidebar|
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
                vuid   = match[1]
                parent = match[2]
                text   = match[3].gsub("\n", ' ')  # Have to forcibly remove newline characters, as for some reason they're translated to the literal string '\n' when converting to json. No idea why.

                # Delete the vuid from the detected vuid list, so we know it's been extracted successfully
                detected_vuid_list.delete(vuid)

                # Generate the table entry
                entry = {'vuid' => vuid, 'text' => text}

                # Initialize the database if needs be
                if map['validation'][parent] == nil
                  map['validation'][parent] = {'core' => []}
                end

                # Add the entry to the table
                if extensions == []
                  map['validation'][parent]['core'] << entry
                else
                  if map['validation'][parent][extensions.join('+')] == nil
                    map['validation'][parent][extensions.join('+')] = []
                  end
                  map['validation'][parent][extensions.join('+')] << entry
                end
              else
                puts "VU Extraction Treeprocessor: WARNING - Valid Usage statement without a VUID found: "
                puts item.text
              end
            end
          end
        end
      end
    end

    # Print out a list of VUIDs that were not extracted
    if detected_vuid_list.length != 0
      puts 'The following VUIDs were not successfully extracted from the spec:'
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
      errors = JSON::Validator.fully_validate(schema, json)

      # Output errors if there were any
      if errors != []
        puts 'VU Extraction JSON Validator: WARNING - Validation of the json schema failed'
        puts 'It is likely that there is an invalid or malformed entry in the specification text,'
        puts 'see below error messages for details, and use their VUIDs and text to correlate them to their location in the specification.'
        puts errors
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
