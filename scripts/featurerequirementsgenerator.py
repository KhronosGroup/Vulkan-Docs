#!/usr/bin/python3 -i
#
# Copyright 2013-2024 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

from generator import OutputGenerator, write
from parse_dependency import dependencyMarkup
import re

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
        
        self.features = dict()
        # <'parent', {'adocstring' : '', 'features' : ['']}
        
        self.removedfeatures = dict()
        # <name, {'parent' : '', 'parentstring' : '', 'removalreasonlink' : ''}>

    # Take a feature token and turn it into a friendly string
    # TODO: Same functionality may exist elsewhere in the scripts and could be re-used instead?
    def featureStringToAdoc(self, featurestring):   
        vmajor = 1
        vminor = 0
        
        # TODO: Handle complex feature strings
        if any(x in featurestring for x in [',','+','(',')']):
            self.logMsg('error', f'Complex dependency expression not currently supported when generating feature requirements: {featurestring}')
        
        # Pull out the version number
        if '_VERSION_' in featurestring:
            pattern = re.compile("[A-Z_]+([0-9])_([0-9])")
            match = pattern.match(featurestring)
            vmajor = match[1]
            vminor = match[2]
        
        # Select between Vulkan, Vulkan SC, and Extensions
        if 'VK_VERSION' in featurestring:
            return 'Vulkan ' + vmajor + '.' + vminor
        elif 'VKSC_VERSION' in featurestring:
            return 'Vulkan SC ' + vmajor + '.' + vminor
        else:
            return '`apiext:' + featurestring + '`'

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
            self.features[name] = dict()
            self.features[name]['features'] = []
            self.features[name]['adocstring'] = adocname
            self.features[name]['dependencies'] = []

            # Get a list of requirement blocks
            requires = interface.findall('./require')
            
            # Loop through and find all the features
            for require in requires:
                requiredfeatures = require.findall('./feature')
            
                for feature in requiredfeatures:
                    self.features[name]['features'].append(feature.get('name'))
                    self.features[name]['dependencies'].append(require.get('depends'))
                
        
        # Find all removed features in this version/extension
        removals = interface.findall('./remove')
        
        # Loop through and record any removals
        for removal in removals:
            reasonlink = removal.get('reasonlink')
                
            removedfeatures = removal.findall('./feature')
            # Note (Tobias): If multiple things remove a feature, only the last one found will be recorded.
            # Not handled at the moment because removals are exceptional and do not currently do this.
            for feature in removedfeatures:
                featurename = feature.get('name')
                self.removedfeatures[featurename] = dict()
                self.removedfeatures[featurename]['parent'] = name
                self.removedfeatures[featurename]['parentstring'] = adocname
                self.removedfeatures[featurename]['reasonlink'] = reasonlink
    
    # Turn a set of extra dependencies on a require block and any removals into spec text that can be appended to a requirement
    def writeExtraDependencyText(self, featuredepends, featurename, indent):
        # TODO: This does not currently handle any complex expressions allowed by the xml (e.g. anything with braces, '+', or ',' symbols)
        if featuredepends != None:
            write(indent + 'if ' + self.featureStringToAdoc(featuredepends) + ' is supported', file=self.outFile)
        
        # Write any exception where a feature is removed by an extension or version
        if featurename in self.removedfeatures.keys():
            write('ifdef::' + self.removedfeatures[featurename]['parent'] + '[]', file=self.outFile)
            if featuredepends != None:
                write(indent + 'and', file=self.outFile)
            else:
                write(indent + 'if', file=self.outFile)
            write(indent + self.removedfeatures[featurename]['parentstring'] + ' is not advertised', file=self.outFile)
            reasonlink = self.removedfeatures[featurename]['reasonlink']
            if reasonlink:
                write(indent + '(see <<' + reasonlink + '>>)', file=self.outFile)
            write('endif::' + self.removedfeatures[featurename]['parent'] + '[]', file=self.outFile)
        
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
                for i in range(len(data['features'])):
                    featuredepends = data['dependencies'][i]
                    featurename = data['features'][i]

                    write('  ** <<features-' + featurename + ',pname:' + featurename + '>>', file=self.outFile)
                    self.writeExtraDependencyText(featuredepends, featurename, '     ');

                
            else:
                # Write the feature requirement
                
                featuredepends = data['dependencies'][0]
                featurename = data['features'][0]               
                
                write('    <<features-' + featurename + ',pname:' + featurename + '>> must: be supported', file=self.outFile)
                
                self.writeExtraDependencyText(featuredepends, featurename, '    ');
                
            # End the file
            write('endif::' + parentname + '[]', file=self.outFile)
            
        OutputGenerator.endFile(self)
    