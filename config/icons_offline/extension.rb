# Copyright (c) 2016-2020 The Khronos Group Inc.
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

class MakeIconsOffline < Extensions::Postprocessor

  FaCDN = /<link rel="stylesheet" href="https:\/\/cdnjs.cloudflare.com\/ajax\/libs\/font-awesome\/[0-9].[0-9].[0-9]\/css\/font-awesome.min.css">/m

  def process document, output

    if document.attr? 'stem'
      fapath = document.attr 'fapath'

      faOffline = '
<!-- Note: Chrome needs crossorigin even for same-origin fonts -->
<link rel="preload" href="../fontawesome/fonts/fontawesome-webfont.woff2?v=4.7.0" as="font" type="font/woff2" crossorigin>
'
      faOffline += '<link rel="stylesheet" href="' + fapath + '/css/font-awesome-custom.min.css">'

      output.sub! FaCDN, faOffline
    end
    output
  end
end
