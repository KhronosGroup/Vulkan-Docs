require 'asciidoctor/extensions'

# This script makes [latexmath] blocks work within table cells.
# See https://github.com/asciidoctor/asciidoctor-pdf/issues/740

Asciidoctor::Extensions.register do
  treeprocessor do
    process do |doc|
      mathematicalProcessor = MathematicalTreeprocessor.new
      (table_blocks = doc.find_by context: :table).each do |table|
        (table.rows[:body] + table.rows[:foot]).each do |row|
          row.each do |cell|
            mathematicalProcessor.process cell.inner_document if cell.style == :asciidoc
          end
        end
      end
    end
  end
end
