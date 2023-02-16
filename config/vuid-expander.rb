# Copyright 2020-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

require 'asciidoctor/extensions' unless RUBY_ENGINE == 'opal'

include ::Asciidoctor

class VUIDExpanderTreeprocessor < Extensions::Treeprocessor
  def process document
    # Find all list items inside Valid Usage sidebar blocks
    document.find_by(context: :sidebar).each do |sidebar|
      # Get sidebar title from instance variable to avoid side-effects from substitutions
      if sidebar.title? and sidebar.instance_variable_get(:@title).start_with? "Valid Usage"
        sidebar.find_by(context: :list_item) do |item|
            # Get item text directly from instance variable to avoid inline substitutions
            original_text = item.instance_variable_get(:@text)
            # Find VUID anchor and append with matching VUID-styled text and line break
            item.text = original_text.gsub(/(\[\[(VUID-[^\]]*)\]\])/, "\\1 [vuid]#\\2# +\n")
        end
      end
    end
    nil
  end
end

Extensions.register do
  treeprocessor VUIDExpanderTreeprocessor
end
