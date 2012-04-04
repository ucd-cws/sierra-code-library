import sys
import arcpy 

from arcgis_utilities.transform_lidar.cwslidar import *

class process_wrapper:

	def __init__(self):
		self.mm_min = arcpy.GetParameterAsText(2) # this occurs here, because it needs to be stored and passed between modules and used again
		self.mm_max = arcpy.GetParameterAsText(3) # down below in the processor method.
		
		if self.mm_min == None:
			log("warning, no minimum!")
		else:
			log("min: %s" % self.mm_min)
		if self.mm_max == None:
			log("warning, no maximum!")
		else:
			log("max: %s" % self.mm_max)						

	def processor(self,data,mm,output = None): # mm is the minmax object
		try:
			mm.min = self.mm_min # set the appropriate values on the minmax object
			mm.max = self.mm_max
		except:
			log("Couldn't set min-max properties")
			raise
			
		try:
			output.write("x y z i r g b\n")
		except:
			log("Couldn't write header")
			raise
			
		for line in data:
			try:
				newmatch = re.search('(^\d+\.?\d*\s+\d+\.?\d*\s+\d+\.?\d*\s+)(-?\d+)(\s+.*)',line) # find the fourth group of numbers and include the sign
				if newmatch is None or newmatch.group(1) is None:
					log("Problem matching line for intensity minmax - point dropped for line %s" % line)
					continue
			except:
				log("Problem reading and scaling intensity - point dropped")
				continue
			
			try:
				stretched = mm.stretch(newmatch.group(2))
			except:
				log("Point dropped - couldn't stretch line %s" % line)
				continue
				
			try:
				new_line = "%s%s%s\n" %(newmatch.group(1),stretched,newmatch.group(3))
				output.write(new_line)
			except:
				log("point dropped - Couldn't write out line where input was %s" % line)

output_dir = arcpy.GetParameterAsText(1)
setup(output_dir)
scaler = process_wrapper()
process_data(scaler)
shutdown()