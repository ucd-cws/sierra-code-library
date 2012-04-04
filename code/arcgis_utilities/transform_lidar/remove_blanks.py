import sys
import arcpy

from arcgis_utilities.transform_lidar.cwslidar import *

class func_wrapper:

	def __init__(self):
		pass

	def processor(self,data,mm,output = None): # mm is the minmax object
		output.write("x y z i r g b\n")
		for line in data:
			match = re.search('^(\d*)\s*$',line) # if this line is just the digits
			if match is not None and match.group(0) is not None: # if it matches
				continue # we don't care about this line
			else:
				try:
					newmatch = re.search('^\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*\s+(-?\d+)\s+',line) # find the fourth group of numbers and include the sign
					if newmatch is not None and newmatch.group(1) is not None:
						mm.track(newmatch.group(1))
					else:
						log("Problem matching line for intensity minmax")
				except:
					log("Problem reading and scaling intensity")
				output.write("%s" % line)
		log(mm.report(return_text = True))

output_dir = arcpy.GetParameterAsText(1)
setup(output_dir)
blanker = func_wrapper()
process_data(blanker)

shutdown()