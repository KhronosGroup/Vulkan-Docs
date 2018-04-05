require 'nokogiri'


renames = {}

extension_name = ARGV[0]
extension_suffix = /VK_([^_]+)_.+/.match(extension_name)[1]

allowed_dependency_renames = ['']

file = File.open("vk.xml")
Nokogiri::XML(file).xpath('//extension[@name="' + extension_name + '"]').each do | extension |
  extension_enum_offset = 1000000000 + ((extension.attribute('number').content.to_i - 1) * 1000)
  extension.xpath('require').each do |require|

    do_rename = false

    if require.attribute('extension')
      allowed_dependency_renames.each do |dependency|
        if require.attribute('extension').content == dependency
          do_rename = true
        end
      end
    else
      do_rename = true
    end

    if do_rename == false
      puts "Extension interaction with " + require.attribute('extension').content + " needs addressing!"
    else
      core_block = "\t"*2 + require.to_s.lines[0].strip + "\n"
      alias_block = "\t"*3 + require.to_s.lines[0].strip + "\n"

      require.children.each do |element|
        if element.node_name != 'text' && element.node_name != 'comment'

          # Core Block
          if /.+_EXTENSION_NAME/.match(element.attribute('name').content) == nil &&
             /.+_SPEC_VERSION/.match(element.attribute('name').content) == nil

            case element.node_name
            when 'enum'
              attributes = element.attributes
              if element.attributes['offset']
                attributes['value'] = element.attribute('offset').content.to_i + extension_enum_offset
                attributes.delete('offset')
              end

              core_block << "\t"*3 + '<enum'
              attributes.each_pair do |key, value|
                core_block << ' ' + key + '="' + value.to_s + '"'
              end
              core_block << '/>' + "\n"
            when 'type', 'command'
              core_block << "\t"*3 + element.to_s.strip + "\n"
            else
              core_block << "Warning: Unknown type found!\n" << element.node_name
            end
          end

          # Alias Block + Renames

          if /.+_EXTENSION_NAME/.match(element.attribute('name').content) ||
             /.+_SPEC_VERSION/.match(element.attribute('name').content)
            alias_block << "\t"*4 + element.to_s.strip + "\n"
          else
            old_name = element.attribute('name').content
            new_name = old_name.sub('_' + extension_suffix,'').sub(extension_suffix,'')
            alias_block << "\t"*4 + '<alias name="' + old_name + '" value="' + new_name + '"/>' + "\n"
            renames[old_name] = new_name
            core_block.gsub!(old_name,new_name)
          end
        end
      end
      alias_block << "\t"*3 + require.to_s.lines[-1].strip
      core_block << "\t"*2 + require.to_s.lines[-1].strip

      puts alias_block
      puts
      puts core_block
      puts
      renames.each_pair do |old, new|
        puts old + ' -> ' + new
      end
    end
  end
end

outdata = File.read('vk.xml')

renames.each_pair do |old, new|
  outdata.gsub!(old,new)
end

File.open('vk.xml', 'w') do |out|
  out << outdata
end

def rename_text_files(dir, renames, extension_name)
  Dir[dir + '/*.txt'].each do |name|
    # Skip renaming in the extension appendix, since this should preserve the old names.
    if (name != ('../appendices/' + extension_name + '.txt'))
      old_file = File.read(name)

      new_file = old_file.clone
      renames.each_pair do |old, new|
        new_file.gsub!(old,new)
      end

      if (old_file != new_file)
        File.write(name, new_file)
      end
    end
  end
  Dir[dir + '/*/'].each do |subdir|
    rename_text_files(subdir, renames, extension_name)
  end
end

rename_text_files('../chapters', renames, extension_name)
rename_text_files('../appendices', renames, extension_name)
