require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

module Asciidoctor

# This addition to the parser class overrides the "is_delimited_block?"
# method of the core parser, adding a new block delimiter of "~~~~" for open
# blocks, which can be extended to an arbitrary number of braces to allow
# nesting them, which is a limitation of the existing "only two dashes"
# delimiter: https://github.com/asciidoctor/asciidoctor/issues/1121
# The choice of tildes is based on comments in that bug.

class Parser
  # Storing the original method so we can still call it from the overriding
  # version
  @OLD_is_delimited_block = method(:is_delimited_block?)

  # Logic here matches the original Parser#is_delimited_block? method, see
  # there for details of base implementation.
  def self.is_delimited_block? line, return_match_data = false
    # Quick check for a single brace character before forwarding to the
    # original parser method.
    if line[0] != '~'
      return @OLD_is_delimited_block.(line, return_match_data)
    else
      line_len = line.length
      if line_len <= 4
        tip = line
        tl = line_len
      else
        tip = line[0..3]
        tl = 4
      end
      
      # Hardcoded tilde delimiter, since that's the only thing this
      # function deals with.
      if tip == '~~~~'
        # tip is the full line when delimiter is minimum length
        if tl < 4 || tl == line_len
          if return_match_data
            context = :open
            masq = ['comment', 'example', 'literal', 'listing', 'pass', 'quote', 'sidebar', 'source', 'verse', 'admonition', 'abstract', 'partintro'].to_set
            BlockMatchData.new(context, masq, tip, tip)
          else
            true
          end
        elsif %(#{tip}#{tip[-1..-1] * (line_len - tl)}) == line
          if return_match_data
            context = :open
            masq = ['comment', 'example', 'literal', 'listing', 'pass', 'quote', 'sidebar', 'source', 'verse', 'admonition', 'abstract', 'partintro'].to_set
            BlockMatchData.new(context, masq, tip, line)
          else
            true
          end
        else
          nil
        end
      else
        nil
      end
    end
  end
end

end