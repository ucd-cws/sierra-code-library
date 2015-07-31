"""
	This script was designed to replace many lines in existing KMLs with corrected lines after some corrections
	needed to be made to already exported data. The replacements are defined in the variable "regexes" as
	two-tuples with what to search for and what to replace it with.
	
	Performancewise, I'd imagine this would be much faster if it kept a compiled object for every regex and 
	used it each time (maybe by replacing the tuples with lists and appending the compiled regex as the last object for each list. If it ever needs to be used again, this could save some time
"""

import os
import re

getpath = os.getcwd()
files = os.listdir(getpath)

linethreshold = 30000 # stops processing after this many lines - in order to speed up

#Fixes to the popup
regexes = [(r'Nitrogen\+Leached\+by\+Scenario\(kg\+N\/ha\)',r'Nitrogen+Leached+by+Scenario+(kg+N)'),
	(r'Standing\+Aboveground\+Carbon\+by\+Scenario\+\(tons\+C\/ha\)',r'Standing+Aboveground+Carbon+by+Scenario+(tons+C)'),
	(r'The total amount of carbon stoed in this parcel',r'The total amount of carbon stored in this parcel'),
	(r'(<tr class=")(r\d)("><td class="a">)(UrbSolarES)(</td>)',r'\1r2\3Urban Solar Scenario\5'),
	(r'(<tr class="r\d"><td class="a">)(UrbSolar)(</td><td class="b">.*?</td></tr>)',""),
	(r'(<tr class="r\d"><td class="a">AgX</td><td class="b">.*?</td></tr>)',""),
	(r'(<tr class="r\d"><td class="a">AgXES</td><td class="b">.*?</td></tr>)',""),
	(r'( closes parcel )',r" closest parcel ")
]

for file in files:
	if ".kml" in file:
		print file
	else:
		continue
	
	outfname = "%s_2" % file
	outfile = open("%s_2" % file, 'w')
	fhandle = open(file, 'r')
	
	
	i = 0
	
	for line in fhandle:
		i += 1
		if i < linethreshold:
			for regex in regexes:
				newline = re.sub(regex[0],regex[1],line)
				if newline != line:
					outfile.write(newline)
					break
			else:
				outfile.write(line)
				
		else:
			outfile.write(line)
	
	outfile.close()
	fhandle.close()
	os.rename(file,"%s_old" % file)
	os.rename(outfname,file)