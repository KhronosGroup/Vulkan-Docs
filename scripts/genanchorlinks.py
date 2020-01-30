#!/usr/bin/python3
#
# Copyright (c) 2020 The Khronos Group Inc.
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

# Script that adds href to <a> anchors

import os,sys,re

def genAnchorLinks(in_file, out_file):
	try:
		with open(in_file, 'r', encoding='utf8') as f: data = f.read()
	except FileNotFoundError:
		print('Error: File %s does not exist.' % in_file)
		sys.exit(2)

	data = re.sub( r'(<a )(id="(VUID\-[\w\-:]+)")(>)', '\g<1>\g<2> href="#\g<3>"\g<4>', data)
	with open(out_file, 'w', encoding='utf8') as f: data = f.write(data)

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print('Error: genanchorlinks.py requires two arguments.')
		print('Usage: genanchorlinks.py infile.html outfile.html')
		sys.exit(1)
	genAnchorLinks(sys.argv[1], sys.argv[2])
