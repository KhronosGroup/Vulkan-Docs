#!/usr/bin/python3
#
# Copyright (c) 2020 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Script that performs the vkspec.html pre-patching needed for chunked

import os,sys,re

def chunkedPatch(in_file, out_file):
	try:
		with open(in_file, 'r', encoding='utf8') as f: data = f.read()
	except FileNotFoundError:
		print('Error: File %s does not exist.' % in_file)
		sys.exit(2)

	chunked_header_stuff = r'''
<link href="chunked.css" rel="stylesheet">
<script>var searchindexurl = 'search.index.js?' + (document.title.replace(/[^0-9.]/g, ''));</script>
<script src="chunked.js"></script>
'''
	chunked_preamble = r'<li><a href="#preamble">0. Preamble</a></li>'
	chunked_searchbox = r'<div class="searchbox"><label for="searchbox">Search: </label><input id="searchbox" type="text" disabled="disabled" value="Loading Search Data" /><div id="resultsdiv"><ol id="results"></ol></div></div>'

	data = re.sub(r'(?=<\/head>)', chunked_header_stuff, data, 1)
	data = re.sub(r'(?<=<ul class="sectlevel1">)', '\n' + chunked_preamble, data, 1)

	# loadable_html extension compat
	data, sub_count = re.subn(r'(?=<\/div>\s*<div id="loading_msg")', chunked_searchbox + '\n', data, 1)
	if sub_count == 0:
		data = re.sub(r'(?=<\/div>\s*<div id="content")', chunked_searchbox + '\n', data, 1)

	with open(out_file, 'w', encoding='utf8') as f: data = f.write(data)

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print('Error: chunked_patch.py requires two arguments.')
		print('Usage: chunked_patch.py infile.html outfile.html')
		sys.exit(1)
	chunkedPatch(sys.argv[1], sys.argv[2])
