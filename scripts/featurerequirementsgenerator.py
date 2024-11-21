#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from parse_dependency import dependencyMarkup
import re
from spec_tools.util import findNamedElem

class FeatureRequirementsDocGenerator(OutputGenerator):
    """FeatureRequirementsDocGenerator - subclass of OutputGenerator.

    Generates AsciiDoc file listing all the required features in the API.
    The fields used from <extension> tags in the API XML are:

    - name          extension name string
    - number        version number
    
    The key data it looks at are the <require> / <remove> tags and the <feature> tags that they contain."""
    
    # Initialize the class
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        
        self.features = {}
        # <'parent', {'adocstring' : '', 'features' : ['']}
        
        self.removedfeatures = {}
        # <name, {'parent' : '', 'parentstring' : '', 'removalreasonlink' : ''}>

    # Take a feature token and turn it into a friendly string
    # TODO: Same functionality may exist elsewhere in the scripts and could be re-used instead?
    def featureStringToAdoc(self, featurestring, addIsSupported=False):
        vmajor = 1
        vminor = 0
        
        # TODO: Handle complex feature strings
        if any(x in featurestring for x in ['(',')']):
            self.logMsg('error', f'Complex dependency expression not currently supported when generating feature requirements: {featurestring}')

        features = []
        conjunction = ''
        
        if ',' in featurestring:
            features = featurestring.split(',')
            conjunction = ' or '
        elif '+' in featurestring:
            features = featurestring.split('+')
            conjunction = ' and '
        else:
            features = [featurestring]
        
        resultstrings = []
        
        for feature in features:
            # Pull out the version number
            if '_VERSION_' in feature:
                pattern = re.compile("[A-Z_]+([0-9])_([0-9])")
                match = pattern.match(feature)
                vmajor = match[1]
                vminor = match[2]
            
            # Select between Vulkan, Vulkan SC, and Extensions
            if 'VK_VERSION' in feature:
                resultstrings.append('Vulkan ' + vmajor + '.' + vminor)
            elif 'VKSC_VERSION' in feature:
                resultstrings.append('Vulkan SC ' + vmajor + '.' + vminor)
            elif '::' in feature:
                featurestruct = feature.split('::')[0]
                featurename = feature.split('::')[1]
                resultstrings.append(self.featuresTolinks(featurestruct,featurename))
            else:
                resultstrings.append('`apiext:' + feature + '`')
                
        isSupportedString = ''
        if addIsSupported:
            isSupportedString = ' is supported'
            if len(resultstrings) > 1:
                isSupportedString = ' are supported'
        
        if len(resultstrings) == 1:
            return resultstrings[0] + isSupportedString
        elif len(resultstrings) == 2:
            return resultstrings[0] + conjunction + resultstrings[1] + isSupportedString
        else:
            return ','.join(resultstrings[0:-2]) + ',' + conjunction + resultstrings[-1] + isSupportedString
            

    # This function records all the added and removed api features by each API version or extension
    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)
                
        # These attributes must exist
        name = self.featureName
        
        # Figure out an asciidoc string tag for the feature or extension
        adocname = self.featureStringToAdoc(name)
        
        # Check for any features in this version/extension   
        if len(interface.findall('./require/feature')) > 0:
            self.features[name] = {}
            self.features[name]['features'] = {}
            self.features[name]['adocstring'] = adocname

            # Get a list of requirement blocks
            requires = interface.findall('./require')
            
            # Loop through and find all the features
            for require in requires:
                requiredfeatures = require.findall('./feature')
            
                for feature in requiredfeatures:
                    featurestruct = feature.get('struct')
                    featurename = feature.get('name')
                    
                    if featurename not in self.features[name]['features']:
                        self.features[name]['features'][featurename] = {}
                        self.features[name]['features'][featurename]['depends'] = {}
                    self.features[name]['features'][featurename]['depends'][require.get('depends')] = 0;
                    self.features[name]['features'][featurename]['struct'] = featurestruct;
                    
                    # Check if a feature is required both unconditionally and conditionally - the unconditional entry will override.
                    if None in self.features[name]['features'][featurename]['depends'] and len(self.features[name]['features'][featurename]['depends'].keys()) > 1:
                        self.features[name]['features'][featurename]['depends'] = { None }
                        self.logMsg('warning', f'The `{featurename}` feature is required both unconditionally and conditionally in {name}')
        
        # Find all removed features in this version/extension
        removals = interface.findall('./remove')
        
        # Loop through and record any removals
        for removal in removals:
            reasonlink = removal.get('reasonlink')
                
            removedfeatures = removal.findall('./feature')
            # Note (Tobias): If multiple things remove a feature, only the last one found will be recorded.
            # Not handled at the moment because removals are exceptional and do not currently do this.
            for feature in removedfeatures:
                featurelist = feature.get('name')
                self.removedfeatures[featurelist] = {}
                self.removedfeatures[featurelist]['parent'] = name
                self.removedfeatures[featurelist]['parentstring'] = adocname
                self.removedfeatures[featurelist]['reasonlink'] = reasonlink
    
    # Turn a set of extra dependencies on a require block and any removals into spec text that can be appended to a requirement
    def writeExtraDependencyText(self, featuredepends, featurelist, indent):
            
        # Write any exception where a feature is removed by an extension or version
        if featurelist in self.removedfeatures.keys():
            write('ifdef::' + self.removedfeatures[featurelist]['parent'] + '[]', file=self.outFile)
            
            # Add a conjunction to the dependency keys if necessary
            joinstring = ''
            if None not in featuredepends.keys():
                joinstring = '; and'

            write(indent + 'if ' + self.removedfeatures[featurelist]['parentstring'] + ' is not advertised' + joinstring, file=self.outFile)
            reasonlink = self.removedfeatures[featurelist]['reasonlink']
            if reasonlink:
                write(indent + '(see <<' + reasonlink + '>>)', file=self.outFile)
            write('endif::' + self.removedfeatures[featurelist]['parent'] + '[]', file=self.outFile)
            

        # If any entry in the dependencies is None then the feature is unconditionally required.
        if None not in featuredepends.keys():
            strings = []
            for featuredepend in featuredepends.keys():
                # TODO: This does not currently handle any complex expressions including parentheses, only simple lists
                strings.append(indent + 'if ' + self.featureStringToAdoc(featuredepend,True))
            
            write(', or \r\n'.join(strings), file=self.outFile)

    # Split a list of features into a linked, human-readable list
    def featuresTolinks(self, featurestruct, featurelist):
        features = featurelist.split(',')
        featuretexts = []
        
        # Lookup the the feature struct
        featurestructinfo = self.registry.lookupElementInfo(featurestruct, self.registry.typedict)
        
        # Iterate through any aliases to find the base struct type
        while featurestructinfo.elem.get('alias') != None:
            featurestructinfo = self.registry.lookupElementInfo(featurestructinfo.elem.get('alias'), self.registry.typedict)
        
        # Iterate through each feature
        for feature in features:
            
            # Get the feature info from the xml
            members = featurestructinfo.getMembers()
            featureelem = findNamedElem(members, feature)
            
            # Check if the struct is listed incorrectly
            if featureelem == None:
                self.logMsg('error', f'Feature struct {featurestruct} incorrectly listed against the `{feature}` feature in the xml.')
            
            # Check for a feature link name (default to name of the feature)
            featurelink = feature
            disambiguator = ''
            if featureelem.get('featurelink') != None:
                featurelink = featureelem.get('featurelink')
                disambiguator = 'sname:' + featurestruct + '::'
            
            # Append link for the feature
            featuretexts.append('<<features-' + featurelink + ',' + disambiguator + 'pname:' + feature + '>>')
        
        if len(featuretexts) == 1:
            return featuretexts[0]
        
        return ', '.join(featuretexts[0:-1]) + ', or ' + featuretexts[-1]
        
    # Loop through all of the recorded features and write them out as a list of requirements, before finalizing the file.
    def endFile(self):
        for parentname,data in self.features.items():
        
            # Write the pre-amble requiring the parent feature
            write('ifdef::' + parentname + '[]', file=self.outFile)
            write('  * If ' + data['adocstring'] + ' is supported,', file=self.outFile)
            
            # Different output depending how many features - 1 is a sentence, more than 1 is a list
            if len(data['features']) > 1:
                write('    the following features must: be supported:', file=self.outFile)
                                
                # List each feature requirement
                for featurelist,featureinfo in data['features'].items():
                    featuredepends = featureinfo['depends']
                    write('  ** ' + self.featuresTolinks(featureinfo['struct'],featurelist), file=self.outFile)
                    self.writeExtraDependencyText(featuredepends, featurelist, '     ');

                
            else:
                # Write the single feature requirement
                for featurelist,featureinfo in data['features'].items():
                    featuredepends = featureinfo['depends']                    
                    write('    ' + self.featuresTolinks(featureinfo['struct'],featurelist) + ' must: be supported', file=self.outFile)
                    
                    self.writeExtraDependencyText(featuredepends, featurelist, '    ');
                
            # End the file
            write('endif::' + parentname + '[]', file=self.outFile)
            
        OutputGenerator.endFile(self)
    