# Copyright 2016-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

module Asciidoctor

class IfDefMismatchPreprocessorReader < PreprocessorReader
  attr_reader :found_conditionals
  attr_reader :warned
  
  class CursorWithAttributes
    attr_reader :cursor
    attr_reader :attributes
    attr_reader :line
    
    def initialize cursor, attributes, line
      @cursor, @attributes, @line = cursor, attributes, line
    end
  end

  def initialize document, lines
    @found_conditionals = Array.new
    super(document,lines)
  end

  def is_adoc_begin_conditional line
    line.start_with?( 'ifdef::', 'ifndef::' ) && line.end_with?('[]')
  end

  def is_adoc_begin_conditional_eval line
    line.start_with?( 'ifeval::[' ) && line.end_with?(']')
  end

  def is_adoc_end_conditional line
    line.start_with?( 'endif::' ) && line.end_with?('[]')
  end

  def conditional_attributes line
    line.delete_prefix('ifdef::').delete_prefix('ifndef::').delete_prefix('endif::').delete_suffix('[]')
  end

  def process_line line
    new_line = line
    if is_adoc_begin_conditional(line)
      # Standard conditionals, add the conditional to a stack to be unwound as endifs are found
      @found_conditionals.push CursorWithAttributes.new cursor, conditional_attributes(line), line
    elsif is_adoc_begin_conditional_eval(line)
      # ifeval conditionals do not have attributes, so store those slightly differently
      @found_conditionals.push CursorWithAttributes.new cursor, '', line
    elsif is_adoc_end_conditional(line)
      # Try to match each endif to a previously defined conditional, logging errors as it goes
      match_found = false
      pop_count = 0
      error_stack = Array.new
      @found_conditionals.reverse_each do |conditional|
        # Try the whole stack to find a match in case there is an extra ifdef in the way
        pop_count += 1
        if conditional.attributes == conditional_attributes(line)
          match_found = true
          break
        end
      end
      
      if match_found
        # First pop any non-matching conditionals and fire a mismatch error
        (pop_count - 1).times do
          # Warn about fixing preprocessor directives before any other issue, as these often cause a domino effect
          if not @warned
            logger.warn "Preprocessor conditional mismatch detected - these should be addressed before attempting to fix any other errors."
            @warned = true
          end
          
          # Log an error 
          conditional = @found_conditionals.pop
          logger.error message_with_context %(unmatched conditional "#{conditional.line}" with no endif), source_location: conditional.cursor
          
          # Insert an endif statement so asciidoctor's default reader does not throw extraneous mismatch errors.
          # This can mess with the way blocks are terminated, but errors will only be thrown if they would have been thrown without this checker; they will just be different.
          #
          # e.g.:
          # [source,c]
          # ----
          # ifdef::undefined_attribute[]
          # Some text
          # ifdef::undefined_attribute[] // should be an endif
          # ----                         // left unparsed because the ifdef is open
          #                              // Script adds 2 'endif::undefined_attribute[]' lines here
          # endif::another_attribute[]   // Irrelevant whether this is defined or not
          #
          # Ideally these errors would be suppressed too, but that requires a lot more complexity; e.g. rewinding the reader back to the ifdef and removing it
          extra_line = %(endif::#{conditional.attributes}[])
          unshift(extra_line)
          super(extra_line)
        end
        
        # Pop the matching conditional
        @found_conditionals.pop
      else
        # Warn about fixing preprocessor directives before any other issue, as these often cause a domino effect
        if not @warned
          logger.warn "Preprocessor conditional mismatch detected - these should be addressed before attempting to fix any other errors."
          @warned = true
        end
        
        # If no match was found, then this is an orphaned endif
        logger.error message_with_context %(unmatched endif - found "#{line}" with no matching conditional begin), source_location: cursor
        
        # Hide the endif so that asciidoctor's default reader does not try to match it anyway 
        new_line = ''
      end
    end
    
    super(new_line)
  end
end

# Preprocessor hook to iterate over ifdefs to prevent them from affecting asciidoctor's processing.
class IfDefMismatchPreprocessor < Extensions::Preprocessor
  def process document, reader
    # Create a new reader to return which raises errors for mismatched conditionals
    reader = IfDefMismatchPreprocessorReader.new(document, reader.lines)
  end
end

end
