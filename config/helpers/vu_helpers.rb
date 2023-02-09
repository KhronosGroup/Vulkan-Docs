# Copyright 2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

def is_codified_vu(vu)
  # This function is identical to isCodifiedVU in vuAST.py. Because the vu is
  # extracted from the asciidoctor list item however, it doesn't need to
  # preprocess it the same way (stripping '*', etc).
  return vu.split("\n")[0] == 'codified-vu'
end

def spawn_vuformatter(attributes)
  # Create a python process as a service to convert VUs.  This avoids
  # creating a process for every VU, parsing the xml etc.
  vupreprocessor = File.expand_path(File.join(__dir__, '..', '..', 'scripts', 'vupreprocessor.py'))
  formatter = IO.popen(['python3', vupreprocessor], 'r+', :err=>[:child, :out])

  # Preprocess the document attributes to extract the versions and extensions that are being
  # built.  Note that this information can be found in the document attributes (placed in
  # specattribs.adoc, which is included first thing in vkspec.adoc)
  #
  # Additionally, to avoid unnecessarily passing a lot of pre-specified attributes that won't be
  # of interest to codified VUs, whatever attribute is already defined at the document level will
  # be skipped when passing attributes to the vu formatter.
  versions, extensions, docattributes = get_build_info(attributes)
  passed = send_build_versions(formatter, versions, extensions)

  return formatter, docattributes, !passed
end

def terminate_vuformatter(formatter)
  # Tell formatter to quit
  formatter.puts 'EXIT'
  formatter.close()
end

def get_build_info(attributes)
  docattributes = Set.new attributes.keys
  # Versions are those in the form of VK_VERSION_X_Y
  versions = docattributes.select { |attr| attr.start_with? "vk_version_" }
  # Extensions are in the form of VK_...., excluding the versions
  extensions = docattributes.select { |attr| attr.start_with? "vk_" and !versions.any? attr }

  return versions, extensions, docattributes
end

def send_build_versions(formatter, versions, extensions)
  formatter.puts 'VERSIONS'
  formatter.puts versions.join(' ')
  formatter.puts extensions.join(' ')
  formatter.puts 'VERSIONS-END'
  formatter.flush

  passed = false
  while not formatter.eof? do
    line = formatter.gets
    if line.start_with? 'VERSIONS'
      # Failure is not expected, but checking just in case.
      if line.strip() == 'VERSIONS-SUCCESS'
        passed = true
      end
      break
    end
    # If there are any error messages, output them
    puts line
  end

  return passed
end

class FormatResult
  PASSED = 0
  FAILED = 1
  ELIMINATED = 2
end

def format_vu(formatter, api, location, attribs, text)
  # See vupreprocessor.py for the format of the message
  formatter.puts 'FORMAT-VU'
  formatter.puts api
  if location.nil?
    formatter.puts '<Need new asciidoctor version>'
    formatter.puts 0
  else
    formatter.puts location.file
    formatter.puts location.lineno
  end
  formatter.puts attribs.keys.zip(attribs.values).join('$')
  formatter.puts text
  formatter.puts 'FORMAT-VU-END'
  formatter.flush

  # Read back the results from the formatter
  messages = []
  formattedText = []
  formattedEnglish = []

  # Get the error messages, if any
  while not formatter.eof? do
    line = formatter.gets
    if line.rstrip() == 'FORMAT-VU'
      break
    end
    messages.append(line.rstrip())
  end

  # Get the formatted text
  passed = FormatResult::FAILED
  isEnglish = false
  while not formatter.eof? do
    line = formatter.gets
    if line.start_with? 'FORMAT-VU'
      if line.strip() == 'FORMAT-VU-SUCCESS'
        passed = FormatResult::PASSED
      elsif line.strip() == 'FORMAT-VU-ELIMINATED'
        passed = FormatResult::ELIMINATED
      elsif line.strip() == 'FORMAT-VU-TEXT'
        isEnglish = true
        next
      end
      break
    end
    if isEnglish
      formattedEnglish.append(line.rstrip())
    else
      formattedText.append(line.rstrip())
    end
  end

  # Output messages, if any, and report failure if that's the case.
  puts messages
  if passed == FormatResult::FAILED
    puts 'ERROR: Build failure with codified VU (see previous messages) (attributes are: ' + attribs.to_s + ')'
    puts 'ERROR: NOTE: asciidoctor does not track include files. If VU is in included file, source file location will be the parent file.'
    puts 'ERROR: NOTE: asciidoctor line info is not always accurate.  Offending VU is:'
    puts text
  end

  return formattedText, formattedEnglish, passed
end

