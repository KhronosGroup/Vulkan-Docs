import os
import shutil

####################
#
# Functions
#
####################

def createTokenList(content, tagA, tagB, offsetB, tagC):

    currentIndex = 0
    nextIndex = content.find(tagA, currentIndex)

    tokenList = []

    while nextIndex != -1:
        currentIndex = nextIndex

        #
        
        currentIndex = content.find(tagB, currentIndex) + offsetB
            
        nextIndex = content.find(tagC, currentIndex)
        token = content[currentIndex:nextIndex]

        #

        tokenList.append(token)
        
        # Process next token
        
        currentIndex = nextIndex
        nextIndex = content.find(tagA, currentIndex)
        
    return tokenList


def saveTokenList(outputFile, header, tokenList):

    tokenList = sorted(tokenList)

    outputFile.write("<h3>%s</h3>" % (header))
    
    lastLetter = ""
    
    for tokenName in tokenList:
    
        currentLetter = tokenName[2]
        
        if currentLetter != lastLetter:
        
            outputFile.write("<h4>%s</h4>" % (currentLetter))
        
            lastLetter = currentLetter 
     
        outputString = '<code class="code"><a class="ulink" href="%s.html" target="content">%s</a></code><br>' % (tokenName, tokenName)
        outputFile.write(outputString + "\n")
        
    outputFile.write("<br>")

####################
#
# Main
#
####################

#
# Loading the Vulkan header file and close the file.
# 

print("Loading Vulkan header file ...")

inputFile = open("../src/vulkan/vulkan.h", "r")

content = inputFile.read()

inputFile.close()

print("... done.")

#
# Setting version number.
#

print("Setting header version ...")

inputFile = open("html_templates/top.html", "r")
inputContent = inputFile.read()
inputFile.close()

currentIndex = content.find('VK_HEADER_VERSION', 0)
currentIndex = content.find(' ', currentIndex) + 1
nextIndex = content.find('\n', currentIndex)

headerVersion = content[currentIndex:nextIndex]

inputContent = inputContent.replace('<!--VERSION-->', 'v1.0.%s' % (headerVersion))

outputFile = open("deploy/top.html", "w")
outputFile.write(inputContent)
outputFile.close()

print("... done.")

#
# Replacing target="_top" with target="content".
#

print("Replacing target tags ...")

for fileName in os.listdir("../out/1.0/man/html"):

    if fileName.endswith(".html"):
        inputFile = open("../out/1.0/man/html/" + fileName, "r")
        inputContent = inputFile.read()
        inputFile.close()
        
        inputContent = inputContent.replace('"_top"', '"content"')

        outputFile = open("deploy/" + fileName, "w")
        outputFile.write(inputContent)
        outputFile.close()
        
print("... done.")        

#
# Generating the list/index HTML file out of vulkan.h.
#

print("Generating index list ...")

outputFile = open("deploy/list.html", "w")

# Writing the HTML header.

outputFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
outputFile.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
outputFile.write('<html xmlns="http://www.w3.org/1999/xhtml">\n')
outputFile.write('<head>\n')
outputFile.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n')
outputFile.write('<title>Vulkan API Reference Pages</title>\n')
outputFile.write('<link rel="stylesheet" type="text/css" href="vkman.css" />\n')
outputFile.write('</head>\n')
outputFile.write('<body>\n')

#
# Process functions.
#

functionList = createTokenList(content, " VKAPI_CALL vk", "vk", 0, "(")

#
# Process structures.
#

structureList = createTokenList(content, "typedef struct Vk", "Vk", 0, " {")

#            
# Process enumerations.
#

enumumerationList = createTokenList(content, "typedef enum Vk", "Vk", 0, " {")

#            
# Process flags.
#

flagList = createTokenList(content, "typedef VkFlags Vk", "s Vk", 2, ";")

#            
# Saving the function links.
#

saveTokenList(outputFile, "Functions", functionList)

#
# Saving the structure links.
#

saveTokenList(outputFile, "Structures", structureList)

#
# Saving the enumeration links.
#

saveTokenList(outputFile, "Enumerations", enumumerationList)

#
# Saving the flag links.
#

saveTokenList(outputFile, "Flags", flagList)

#
# Writing the HTML footer.
#

outputFile.write('</body>\n')
outputFile.write('</html>\n')

outputFile.close()

print("... done.")

#
# Copying files, which do not need to be modified.
#

print("Copying files ...")

shutil.copyfile("html_templates/index.html", "deploy/index.html")
shutil.copyfile("html_templates/bottom.html", "deploy/bottom.html")
shutil.copyfile("images/Vulkan.png", "deploy/Vulkan.png")
shutil.copyfile("../out/1.0/man/html/vkman.css", "deploy/vkman.css")   
        
print("... done.")        
