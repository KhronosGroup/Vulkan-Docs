#!/usr/bin/python3 -i
#
# Copyright (c) 2019 The Khronos Group Inc.
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

import os
import re
import sys
from generator import (GeneratorOptions, OutputGenerator, noneStr,
                       regSortFeatures, write)

# QuickRefOutputGenerator - subclass of OutputGenerator.
# Generates C-language API interfaces.
#
# ---- methods ----
# QuickRefOutputGenerator(errFile, warnFile, diagFile) - args as for
#   OutputGenerator. Defines additional internal state.
# ---- methods overriding base class ----
# beginFile(genOpts)
# endFile()
# beginFeature(interface, emit)
# endFeature()
# genType(typeinfo,name)
# genStruct(typeinfo,name)
# genGroup(groupinfo,name)
# genEnum(enuminfo, name)
# genCmd(cmdinfo)
class QuickRefOutputGenerator(OutputGenerator):
    """Generate specified API interfaces in a specific style, such as a C header"""
    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = ['include', 'define', 'basetype', 'handle', 'enum',
                     'group', 'bitmask', 'funcpointer', 'struct']
    ALL_SECTIONS = TYPE_SECTIONS + ['commandPointer', 'command']

    REF_LINK = "https://www.khronos.org/registry/vulkan/specs/1.1-extensions/man/html/"

    HEADER_TMPL = """
<div id='{}' class='section'>
 <h1>{}</h1>
 <div class='items'>
  <ul>
"""
    BODY_TMPL = """
<li>
 <pre><code>{}</code></pre>
</li>
"""

    FOOTER_TMPL = """
  </ul>
 </div>
</div>
"""

    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        self.sections = {section: {} for section in self.ALL_SECTIONS}

    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)

    def endFile(self):
        header = """
<!doctype html5>
<html>
 <head>
  <meta charset="utf-8">
  <title>Vulkan Quick Reference</title>
  <style>
   * { box-sizing: border-box; }
   html,
   body {
     margin: 0;
     padding: 0;
   }
   body {
     background-color: #952a29;
     margin: 1em;
   }
   body > h1 {
     color: white;
   }
   div.items {
     columns: 32em;
     column-rule-color: #952a29;
     column-rule-style: double;
     column-rule-width: 4px;
   }
   ul {
     margin: 0;
     padding: 0;
   }
   li {
     list-style-type: none;
     -webkit-column-break-inside: avoid;
     overflow: auto;
   }
   a {
     text-decoration: none;
     background-color: #eee;
     padding: 2px;
     margin: 2px;
     border-radius: 5px;
   }
   .struct-name { color: green; }
   .function-name { color: blue; }
   .section {
     border-radius: 4px;
     box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
     margin-bottom: 1em;
     padding: 1em;
   }
   .section > h1 {
     padding: 0;
     margin: 0;
   }
   #cmd-ptr-and-instance,
   #dispatch,
   #wsi,
   #vtex-post,
   #resource-create,
   #render-pass {
     background-color: #ebf1e9;
   }

   #extend,
   #mem-alloc,
   #vtex-input,
   #blend-facts,
   #queries {
     background-color: #e4e8f0;
   }

   #struct-and-elem,
   #raster,
   #copy-cmds,
   #res-desc,
   #dev-and-queue,
   #pipelines {
     background-color: #fffcd9
   }

   #cmd-buffers,
   #sparse,
   #draw-cmds,
   #samplers {
     background-color: #e4dde9;
   }

   #sync-and-cache,
   #feat-lim-formats,
   #frag-ops,
   #clr-cmds,
   #shaders,
   #remaining {
     background-color: #fcecd8;
   }
  </style>
 </head>
 <body>
  <h1>Vulkan 1.1 Quick Reference Guide</h1>
"""

        footer = """
 </body>
</html>
"""

        write(header, file=self.outFile)

        self.struct_and_cmd = []
        self.struct_and_cmd.extend(self.sections['struct'].keys())
        self.struct_and_cmd.extend(self.sections['command'].keys())
        self.struct_and_cmd.sort()

        # Each of these remove their displayed items from struct_and_cmd
        self.writeCommandFunctionPointersAndInstances()
        self.writeDeviceAndQueues()
        self.writeCommandBuffers()
        self.writeSyncAndCacheControl()
        self.writeRenderPass()
        self.writeShaders()
        self.writePipelines()
        self.writeMemoryAlloc()
        self.writeResourceCreation()
        self.writeSamplers()
        self.writeResourceDescriptors()
        self.writeQueries()
        self.writeClearCommands()
        self.writeDrawCommands()
        self.writeCopyCommands()
        self.writeFixedFuncVertexPostProcessing()
        self.writeVertexInputDesc()
        self.writeFragmentOperations()
        self.writeRasterization()
        self.writeBlendFactors()
        self.writeDispatchCommands()
        self.writeSparseResources()
        self.writeWindowSystem()
        self.writeExtended()
        self.writeFeaturesLimitsAndFormats()

        self.writeRemaining()

        self.writeStructsAndEnums()

        write(footer, file=self.outFile)

        OutputGenerator.endFile(self)

    def writeRender(self, title, id, keys, delete=True):
        write(self.HEADER_TMPL.format(id, title), file=self.outFile)

        for key in keys:
            if delete:
                self.struct_and_cmd.remove(key)

            code = ''
            if key in self.sections['struct']:
                code = self.sections['struct'][key]
            else:
                code = self.sections['command'][key]

            write(self.BODY_TMPL.format(code), file=self.outFile)

        write(self.FOOTER_TMPL, file=self.outFile)

    def writeRemaining(self):
        self.writeRender('Remaining', 'remaining', self.struct_and_cmd, False)

    def writeFeaturesLimitsAndFormats(self):
        keys = [key for key in self.struct_and_cmd if 'Features' in key or
                'Format' in key or
                'External' in key]
        self.writeRender('Features, Limits, and Formats', 'feat-lim-formats', keys)

    def writeExtended(self):
        keys = [key for key in self.struct_and_cmd if 'Enumerate' in key or
                'LayerProp' in key or
                'External' in key or
                'ExtensionProperties' in key]
        self.writeRender('Extended Functionality', 'extend', keys)

    def writeWindowSystem(self):
        keys = [key for key in self.struct_and_cmd if 'Surface' in key or
                'Display' in key or
                'Present' in key or
                'Swapchain' in key or
                'AcquireNext' in key or
                'RectLayer' in key]
        self.writeRender('Window System Integration (WSI)', 'wsi', keys)

    def writeSparseResources(self):
        keys = [key for key in self.struct_and_cmd if 'Sparse' in key or
                'SetDepthBias' in key]
        self.writeRender('Sparse Resources', 'sparse', keys)

    def writeDispatchCommands(self):
        keys = [key for key in self.struct_and_cmd if 'Dispatch' in key]
        self.writeRender('Dispatching Commands', 'dispatch', keys)

    def writeBlendFactors(self):
        keys = [key for key in self.struct_and_cmd if 'SetBlendConst' in key]
        self.writeRender('Framebuffer: Blend Factors', 'blend-facts', keys)

    def writeRasterization(self):
        keys = [key for key in self.struct_and_cmd if 'SetLineWidth' in key or
                'SetDepthBias' in key]
        self.writeRender('Rasterization', 'raster', keys)

    def writeFragmentOperations(self):
        keys = [key for key in self.struct_and_cmd if 'Scissor' in key or
                'SetDepthBounds' in key or
                'SetStencil' in key]
        self.writeRender('Fragment Operations', 'frag-ops', keys)

    def writeVertexInputDesc(self):
        keys = [key for key in self.struct_and_cmd if 'BindVertexBuffers' in key]
        self.writeRender('Vertex Input Description', 'vtex-input', keys)

    def writeFixedFuncVertexPostProcessing(self):
        keys = [key for key in self.struct_and_cmd if 'SetViewport' in key]
        self.writeRender('Fixed-Function Vertex Postprocessing', 'vtex-post', keys)

    def writeCopyCommands(self):
        keys = [key for key in self.struct_and_cmd if 'Copy' in key or
                'Blit' in key or
                'Blit' in key or
                'Resolve' in key]
        self.writeRender('Copy Commands', 'copy-cmds', keys)

    def writeDrawCommands(self):
        keys = [key for key in self.struct_and_cmd if 'Draw' in key or
                'BindIndex' in key]
        self.writeRender('Draw Commands', 'draw-cmds', keys)

    def writeClearCommands(self):
        keys = [key for key in self.struct_and_cmd if 'Clear' in key or
                'FillBuffer' in key or
                'UpdateBuffer' in key]
        self.writeRender('Clear Commands', 'clr-cmds', keys)

    def writeQueries(self):
        keys = [key for key in self.struct_and_cmd if 'Query' in key or
                'WriteTimestamp' in key]
        self.writeRender('Queries', 'queries', keys)

    def writeResourceDescriptors(self):
        keys = [key for key in self.struct_and_cmd if 'Descriptor' in key or
                'PushConstant' in key]
        self.writeRender('Resource Descriptors', 'res-desc', keys)

    def writeSamplers(self):
        keys = [key for key in self.struct_and_cmd if 'Sampler' in key]
        self.writeRender('Samplers', 'samplers', keys)

    def writeResourceCreation(self):
        keys = [key for key in self.struct_and_cmd if 'Buffer' in key or
                'Image' in key or
                'Subresource' in key or
                'ComponentMapping' in key]
        keys = [key for key in keys if 'UpdateBuffer' not in key and
                'FillBuffer' not in key and
                'Clear' not in key and
                'Format' not in key and
                'BindIndexBuffer' not in key and
                'AcquireNext' not in key and
                'Blit' not in key and
                'Resolve' not in key and
                'Copy' not in key and
                'BindVertexBuffers' not in key and
                'Sparse' not in key and
                'Swapchain' not in key]
        self.writeRender('Resource Creation', 'resource-create', keys)

    def writeMemoryAlloc(self):
        keys = [key for key in self.struct_and_cmd if 'Memory' in key]
        keys = [key for key in keys if 'Sparse' not in key]
        self.writeRender('Memory Allocation', 'mem-alloc', keys)

    def writePipelines(self):
        keys = [key for key in self.struct_and_cmd if 'Pipeline' in key or
                'VertexInputAttribute' in key or
                'StencilOpState' in key or
                'VertexInputBinding' in key]
        self.writeRender('Pipelines', 'pipelines', keys)

    def writeShaders(self):
        keys = [key for key in self.struct_and_cmd if 'ShaderModule' in key]
        self.writeRender('Shaders', 'shaders', keys)

    def writeRenderPass(self):
        keys = [key for key in self.struct_and_cmd if 'RenderPass' in key or
                'Attachment' in key or
                'Subpass' in key or
                'Framebuffer' in key or
                'RenderArea' in key]
        keys = [key for key in keys if 'ClearAttachment' not in key]
        self.writeRender('Render Pass', 'render-pass', keys)

    def writeSyncAndCacheControl(self):
        keys = [key for key in self.struct_and_cmd if 'Fence' in key or
                'Semaphore' in key or
                'Event' in key or
                'Barrier' in key or
                'WaitIdle' in key]
        self.writeRender('Synchronization and Cache Control', 'sync-and-cache', keys)

    def writeCommandBuffers(self):
        keys = [key for key in self.struct_and_cmd if 'CommandPool' in key or
            'CommandBuffer' in key or
            'VkSubmitInfo' in key or
            'Execute' in key]
        self.writeRender('Command Buffers', 'cmd-buffers', keys)

    def writeDeviceAndQueues(self):
        keys = [key for key in self.struct_and_cmd if 'Device' in key or
            'Queue' in key]
        keys = [key for key in keys if 'Bind' not in key and
                    'CommandBuffer' not in key and
                    'RenderPass' not in key and
                    'Present' not in key and
                    'PhysicalDeviceFeatures' not in key and
                    'PhysicalDeviceFormat' not in key and
                    'PhysicalDeviceImageFormat' not in key and
                    'PhysicalDeviceExternal' not in key and
                    'PhysicalDeviceMemory' not in key and
                    'PhysicalDeviceSparse' not in key and
                    'PhysicalDeviceDisplay' not in key and
                    'PhysicalDeviceSurface' not in key and
                    'Win32' not in key and
                    'Xcb' not in key and
                    'Wayland' not in key and
                    'Xlib' not in key and
                    'WaitIdle' not in key]
        self.writeRender('Devices and Queues', 'dev-and-queue', keys)

    def writeCommandFunctionPointersAndInstances(self):
        keys = [key for key in self.struct_and_cmd if 'Instance' in key or
            'DeviceProc' in key or
            'Application' in key]
        keys = [key for key in keys if 'EnumerateInstanceLayer' not in key and
            'EnumerateInstanceExtension' not in key]
        self.writeRender('Command Function Pointers and Instances', 'cmd-ptr-and-instance', keys)

    def writeStructsAndEnums(self):
        write(self.HEADER_TMPL.format('struct-and-elem', 'Structures and Enumerations'), file=self.outFile)

        keys = []
        keys.extend(self.sections['struct'].keys())
        keys.extend(self.sections['group'].keys())
        keys.sort()

        for key in keys:
            code = ''
            if key in self.sections['struct']:
                code = self.sections['struct'][key]
            else:
                code = self.sections['group'][key]

            write(self.BODY_TMPL.format(code), file=self.outFile)

        write(self.FOOTER_TMPL, file=self.outFile)

    # Append a definition to the specified section
    def appendSection(self, section, key, text):
        self.sections[section][key] = text

    # Type generation
    def genType(self, typeinfo, name, alias):
        OutputGenerator.genType(self, typeinfo, name, alias)
        typeElem = typeinfo.elem

        category = typeElem.get('category')
        if category in ('struct', 'union'):
            self.genStruct(typeinfo, name, alias)

    # Struct (e.g. C "struct" type) generation.
    def genStruct(self, typeinfo, typeName, alias):
        OutputGenerator.genStruct(self, typeinfo, typeName, alias)

        typeElem = typeinfo.elem
        body = '<a href="' + self.REF_LINK + typeName + '.html">' + typeElem.get('category')
        body += ' <span class="struct-name">' + typeName + '</span></a>\n'

        for member in typeElem.findall('.//member'):
            body += self.makeCParamDecl(member, 1)
            body += '\n'

        self.appendSection('struct', typeName, body)

    # Group (e.g. C "enum" type) generation.
    def genGroup(self, groupinfo, groupName, alias = None):
        OutputGenerator.genGroup(self, groupinfo, groupName, alias)
        groupElem = groupinfo.elem

        body = 'enum <a href="' + self.REF_LINK + groupName + '.html">' + groupName + "</a>\n"

        enumerants = [elem.get('name') for elem in groupElem.findall('enum')]
        enumerants.sort()
        for name in enumerants:
            body += "  " + name + "\n"

        self.appendSection('group', groupName, body)

    # Enumerant generation
    def genEnum(self, enuminfo, name, alias):
        OutputGenerator.genEnum(self, enuminfo, name, alias)
        body = '#define ' + name.ljust(33)
        self.appendSection('define', name, body)

    # Command generation
    def genCmd(self, cmdinfo, name, alias):
        OutputGenerator.genCmd(self, cmdinfo, name, alias)

        cmd = cmdinfo.elem
        proto = cmd.find('proto')
        params = cmd.findall('param')
        # Begin accumulating prototype and typedef strings
        pdecl = self.genOpts.apicall

        # Insert the function return type/name.
        # For prototypes, add APIENTRY macro before the name
        # For typedefs, add (APIENTRY *<name>) around the name and
        #   use the PFN_cmdnameproc naming convention.
        # Done by walking the tree for <proto> element by element.
        # etree has elem.text followed by (elem[i], elem[i].tail)
        #   for each child element and any following text
        # Leading text
        pdecl += noneStr(proto.text)

        # For each child element, if it's a <name> wrap in appropriate
        # declaration. Otherwise append its contents and tail contents.
        for elem in proto:
            text = noneStr(elem.text)
            tail = noneStr(elem.tail)
            if elem.tag == 'name':
                pdecl += '<a href="' + self.REF_LINK + text + '.html"><span class="function-name">' + self.makeProtoName(text, tail) + '</span></a>'
            else:
                pdecl += text + tail

        # Now add the parameter declaration list, which is identical
        # for prototypes and typedefs. Concatenate all the text from
        # a <param> node without the tags. No tree walking required
        # since all tags are ignored.
        # Uses: self.indentFuncProto
        # self.indentFuncPointer
        # self.alignFuncParam
        n = len(params)
        # Indented parameters
        if n > 0:
            indentdecl = '(\n'
            indentdecl += ',\n'.join(self.makeCParamDecl(p, self.genOpts.alignFuncParam)
                                     for p in params)
            indentdecl += ');'
        else:
            indentdecl = '(void);'
        # Non-indented parameters
        paramdecl = '('
        if n > 0:
            paramnames = (''.join(t for t in p.itertext())
                          for p in params)
            paramdecl += ', '.join(paramnames)
        else:
            paramdecl += 'void'
        paramdecl += ");"

        decl = pdecl + indentdecl

        self.appendSection('command', name, decl + '\n')
