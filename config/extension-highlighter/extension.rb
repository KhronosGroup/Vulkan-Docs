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

# Duplicate of "AnyListRx" defined by asciidoctor
# Detects the start of any list item.
#
# NOTE we only have to check as far as the blank character because we know it means non-whitespace follows.
HighlighterAnyListRx = /^(?:#{CG_BLANK}*(?:-|([*.\u2022])\1{0,4}|\d+\.|[a-zA-Z]\.|[IVXivx]+\))#{CG_BLANK}|#{CG_BLANK}*.*?(?::{2,4}|;;)(?:$|#{CG_BLANK})|<?\d+>#{CG_BLANK})/

class ExtensionHighlighterPreprocessorReader < PreprocessorReader
  def initialize document, diff_extensions, data = nil, cursor = nil
    super(document, data, cursor)
    @status_stack = []
    @diff_extensions = diff_extensions
    @tracking_target = nil
  end
  
  # This overrides the default preprocessor reader conditional logic such
  # that any extensions which need highlighting and are enabled have their
  # ifdefs left intact.
  def preprocess_conditional_directive directive, target, delimiter, text
    # If we're tracking a target for highlighting already, don't need to do
    # additional processing unless we hit the end of that conditional
    # section
    # NOTE: This will break if for some absurd reason someone nests the same
    # conditional inside itself.
    if @tracking_target != nil && directive == 'endif' && @tracking_target == target.downcase
      @tracking_target = nil
    elsif @tracking_target
      return super(directive, target, delimiter, text)
    end

    # If it's an ifdef or ifndef, push the directive onto a stack
    # If it's an endif, pop the last one off.
    # This is done to apply the next bit of logic to both the start and end
    # of an conditional block correctly
    status = directive
    if directive == 'endif'
      status = @status_stack.pop
    else
      @status_stack.push status
    end

    # If the status is negative, we need to still include the conditional
    # text for the highlighter, so we replace the requirement for the
    # extension attribute in question to be not defined with an
    # always-undefined attribute, so that it evaluates to true when it needs
    # to.
    # Undefined attribute is currently just the extension with "_undefined"
    # appended to it.
    modified_target = target.downcase
    if status == 'ifndef'
      @diff_extensions.each do | extension |
        modified_target.gsub!(extension, extension + '_undefined')
      end
    end

    # Call the original preprocessor
    result = super(directive, modified_target, delimiter, text)

    # If any of the extensions are in the target, and the conditional text
    # isn't flagged to be skipped, return false to prevent the preprocessor
    # from removing the line from the processed source.
    unless @skipping
      @diff_extensions.each do | extension |
        if target.downcase.include?(extension)
          if directive != 'endif'
            @tracking_target = target.downcase
          end
          return false
        end
      end
    end
    return result
  end
  
  # Identical to preprocess_conditional_directive, but older versions of
  # Asciidoctor used a different name, so this is there to override the same
  # method in older versions.
  # This is a pure c+p job for awkward inheritance reasons (see use of
  # the super() keyword :|)
  # At some point, will rewrite to avoid this mess, but this fixes things
  # for now without breaking things for anyone.
  def preprocess_conditional_inclusion directive, target, delimiter, text
    # If we're tracking a target for highlighting already, don't need to do
    # additional processing unless we hit the end of that conditional
    # section
    # NOTE: This will break if for some absurd reason someone nests the same
    # conditional inside itself.
    if @tracking_target != nil && directive == 'endif' && @tracking_target == target.downcase
      @tracking_target = nil
    elsif @tracking_target
      return super(directive, target, delimiter, text)
    end

    # If it's an ifdef or ifndef, push the directive onto a stack
    # If it's an endif, pop the last one off.
    # This is done to apply the next bit of logic to both the start and end
    # of an conditional block correctly
    status = directive
    if directive == 'endif'
      status = @status_stack.pop
    else
      @status_stack.push status
    end

    # If the status is negative, we need to still include the conditional
    # text for the highlighter, so we replace the requirement for the
    # extension attribute in question to be not defined with an
    # always-undefined attribute, so that it evaluates to true when it needs
    # to.
    # Undefined attribute is currently just the extension with "_undefined"
    # appended to it.
    modified_target = target.downcase
    if status == 'ifndef'
      @diff_extensions.each do | extension |
        modified_target.gsub!(extension, extension + '_undefined')
      end
    end

    # Call the original preprocessor
    result = super(directive, modified_target, delimiter, text)

    # If any of the extensions are in the target, and the conditional text
    # isn't flagged to be skipped, return false to prevent the preprocessor
    # from removing the line from the processed source.
    unless @skipping
      @diff_extensions.each do | extension |
        if target.downcase.include?(extension)
          if directive != 'endif'
            @tracking_target = target.downcase
          end
          return false
        end
      end
    end
    return result
  end
end

class Highlighter
  def initialize
    @delimiter_stack = []
    @current_anchor = 1
  end

  def highlight_marks line, previous_line, next_line
    if !(line.start_with? 'endif')
      # Any intact "ifdefs" are sections added by an extension, and
      # "ifndefs" are sections removed.
      # Currently don't track *which* extension(s) is/are responsible for
      # the addition or removal - though it would be possible to add it.
      if line.start_with? 'ifdef'
        role = 'added'
      else # if line.start_with? 'ifndef'
        role = 'removed'
      end

      # Create an anchor with the current anchor number
      anchor = '[[difference' + @current_anchor.to_s + ']]'

      # Figure out which markup to use based on the surrounding text
      # This is robust enough as far as I can tell, though we may want to do
      # something more generic later since currently it relies on the fact
      # that if you start inside a list or paragraph, you'll end in the same
      # list or paragraph and not cross to other blocks.
      # In practice it *might just work* but it also might not.
      # May need to consider what to do about this in future - maybe just
      # use open blocks for everything?
      highlight_delimiter = :inline
      if (HighlighterAnyListRx.match(next_line) != nil)
        # NOTE: There's a corner case here that should never be hit (famous last words)
        # If a line in the middle of a paragraph begins with an asterisk and
        # then whitespace, this will think it's a list item and use the
        # wrong delimiter.
        # That shouldn't be a problem in practice though, it just might look
        # a little weird.
        highlight_delimiter = :list
      elsif previous_line.strip.empty?
        highlight_delimiter = :block
      end

      # Add the delimiter to the stack for the matching 'endif' to consume
      @delimiter_stack.push highlight_delimiter

      # Add an appropriate method of delimiting the highlighted areas based
      # on the surrounding text determined above.
      if highlight_delimiter == :block
        return ['', anchor, ":role: #{role}", '']
      elsif highlight_delimiter == :list
        return ['', anchor, "[.#{role}]", '~~~~~~~~~~~~~~~~~~~~', '']
      else #if highlight_delimiter == :inline
        return [anchor + ' [.' + role + ']##']
      end
    else  # if !(line.start_with? 'endif')
      # Increment the anchor when we see a matching endif, and generate a
      # link to the next diff section
      @current_anchor = @current_anchor + 1
      anchor_link = '<<difference' + @current_anchor.to_s + ', =>>>'

      # Close the delimited area according to the previously determined
      # delimiter
      highlight_delimiter = @delimiter_stack.pop
      if highlight_delimiter == :block
        return [anchor_link, '', ':role:', '']
      elsif highlight_delimiter == :list
        return [anchor_link, '~~~~~~~~~~~~~~~~~~~~', '']
      else #if highlight_delimiter == :inline
        return [anchor_link + '##']
      end
    end
  end
end

# Preprocessor hook to iterate over ifdefs to prevent them from affecting asciidoctor's processing.
class ExtensionHighlighterPreprocessor < Extensions::Preprocessor
  def process document, reader

    # Only attempt to highlight extensions that are also enabled - if one
    # isn't, warn about it and skip highlighting that extension.
    diff_extensions = document.attributes['diff_extensions'].downcase.split(' ')
    actual_diff_extensions = []
    diff_extensions.each do | extension |
      if document.attributes.has_key?(extension)
        actual_diff_extensions << extension
      else
        puts 'The ' + extension + ' extension is not enabled - changes will not be highlighted.'
      end
    end

    # Create a new reader to return, which leaves extension ifdefs that need highlighting intact beyond the preprocess step.
    extension_preprocessor_reader = ExtensionHighlighterPreprocessorReader.new(document, actual_diff_extensions, reader.lines)

    highlighter = Highlighter.new
    new_lines = []

    # Store the old lines so we can reference them in a non-trivial fashion
    old_lines = extension_preprocessor_reader.read_lines()
    old_lines.each_index do | index |

      # Grab the previously processed line
      # This is used by the highlighter to figure out if the highlight will
      # be inline, or part of a block.
      if index > 0
        previous_line = old_lines[index - 1]
      else
        previous_line = ''
      end

      # Current line to process
      line = old_lines[index]

      # Grab the next line to process
      # This is used by the highlighter to figure out if the highlight is
      # between list elements or not - which need special handling.
      if index < (old_lines.length - 1)
        next_line = old_lines[index + 1]
      else
        next_line = ''
      end

      # Highlight any preprocessor directives that were left intact by the
      # custom preprocessor reader.
      if line.start_with?( 'ifdef::', 'ifndef::', 'endif::')
        new_lines += highlighter.highlight_marks(line, previous_line, next_line)
      else
        new_lines << line
      end
    end

    # Return a new reader after preprocessing - this takes care of creating
    # the AST from the new source.
    Reader.new(new_lines)
  end
end

class AddHighlighterCSS < Extensions::Postprocessor
  HighlighterStyleCSS = [
    '.added {',
    '    background-color: lime;',
    '    border-color: green;',
    '    padding:1px;',
    '}',
    '.removed {',
    '    background-color: pink;',
    '    border-color: red;',
    '    padding:1px;',
    '}',
    '</style>']

  def process document, output
    output.sub! '</style>', HighlighterStyleCSS.join("\n")
  end
end

end
