#!/usr/bin/env ruby
#
# Copyright (c) 2019 Baldur Karlsson
#
# SPDX-License-Identifier: Apache-2.0

require 'pp'
require 'json'

data = []

ARGV.each do |file|

  curdata = nil
  extappendix = false
  curext = ""

  File.readlines(file).each do |line|

    text = line.gsub(/<\/?[^>]*>/, "")

    # Special case - set up high quality results for given structs
    if line =~ /div id="([vV][kK][^"]*)"/ then
      id = $1

      data << { :id => File.basename(file) + "#" + id, :title => id, :body => id }
    end

    if line =~ /h[0-9]\s*id="([^"]*)"/ then

      id = $1

      if curdata != nil then
        data << curdata
      end

      if text =~ /Appendix.*Extensions/ then
        extappendix = true
      end

      if extappendix and text =~ /^VK_.*/ then
        curext = text
      elsif curext != "" then
        text = "#{curext.strip} - #{text}"
      end

      curdata = { :id => File.basename(file) + "#" + id, :title => text, :body => "" }
    elsif curdata != nil then
      curdata[:body] += " " + text
    end

  end

  if curdata != nil then
    data << curdata
  end

end

puts JSON.generate(data)
