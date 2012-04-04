import sys
import arcpy

from arcgis_utilities.transform_lidar.cwslidar import *

class func_wrapper:

	def __init__(self):
		pass

	def processor(self,data,mm,output = None): # mm is the minmax object
		for line in data:
			try:
				newmatch = re.search('^\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*\s+(-?\d+)\s+',line) # find the fourth group of numbers and include the sign
				if newmatch is not None and newmatch.group(1) is not None:
					mm.track(newmatch.group(1))
				else:
					log("line dropped - Problem matching line for intensity minmax - %s" % line)
			except:
				log("Problem reading and scaling intensity")
		
		log(mm.report(return_text = True))

setup()
reporter = func_wrapper()
process_data(reporter)

shutdown()