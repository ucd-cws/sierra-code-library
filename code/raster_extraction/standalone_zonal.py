'''this module is an alternative way to call zonal_stats. The issue is that in ArcGIS 10, having zones too small to capture any cells
causes a crash in the entire interpreter (regardless of exception handling). So, we want to crash a separate interpreter, catch that crash, and proceed'''

import sys

import zonal_stats
import log # this will create some interesting issues in the log where it's adding a ton of new "runs"

zones = sys.argv[1] 
raster = sys.argv[2]
zone_field = sys.argv[3]
filename = sys.argv[4]
output_location = [5]

# this error checking isn't super substantive
if not filename or filename == "":
	filename = None
if not output_location or output_location == "":
	output_location = None

if not zones or not raster or not zone_field:
	log.error("Can't run zonal_stats without zones, raster, and zone_field")
	sys.exit(1)

try:
	output_file = zonal_stats.zonal_stats(zones,raster,zone_field,filename,output_location)
	log.write(output_file,True)
except:
	log.error("Interpreter crash - continuing")
	sys.exit(1) # exit with a failure

sys.exit(0) # specify zero - it defaults here, but that's ok