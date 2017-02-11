# Copyright (c) 2016-2017 The Khronos Group Inc.
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

module Asciidoctor
module Pdf
class Converter < ::Prawn::Document
  def convert_sidebar node
    add_dest_for_block node if node.id
    theme_margin :block, :top
    keep_together do |box_height = nil|
      start_page_number = page_number
      start_cursor = cursor
      # FIXME? Have to draw graphics once before content to get accurate box_height.
      # This is overwritten by the theme_fill_and_stroke_bounds command, so needs drawing twice
      pad_box @theme.sidebar_padding do
        if node.title?
          theme_font :sidebar_title do
            # QUESTION should we allow margins of sidebar title to be customized?
            layout_heading node.title, align: (@theme.sidebar_title_align || @theme.base_align).to_sym, margin_top: 0
          end
        end
        theme_font :sidebar do
          convert_content_for_block node
        end
      end
      
      if box_height
        page_spread = (end_page_number = page_number) - start_page_number + 1
        end_cursor = cursor
        go_to_page start_page_number
        move_cursor_to start_cursor
        page_spread.times do |i|
          if i == 0
            y_draw = cursor
            b_height = page_spread > 1 ? y_draw : (y_draw - end_cursor)
          else
            bounds.move_past_bottom
            y_draw = cursor
            b_height = page_spread - 1 == i ? (y_draw - end_cursor) : y_draw
          end
          bounding_box [0, y_draw], width: bounds.width, height: b_height do
            theme_fill_and_stroke_bounds :sidebar
          end
        end
      end
      
      go_to_page start_page_number
      move_cursor_to start_cursor
      pad_box @theme.sidebar_padding do
        if node.title?
          theme_font :sidebar_title do
            # HACK: The "margin_top: 1" makes things work, but I don't know entirely why.
            # Using the blockquote_padding above instead of sidebar_padding makes the blocks render with the wrong padding.
            # Using the sidebar_padding it loses the background on subsequent pages unless margin_top is 1 here.
            # QUESTION should we allow margins of sidebar title to be customized? 
            layout_heading node.title, align: (@theme.sidebar_title_align || @theme.base_align).to_sym, margin_top: 1
          end
        end
        theme_font :sidebar do
          convert_content_for_block node
        end
      end
    end
    theme_margin :block, :bottom
  end
end
end
end
