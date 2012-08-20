'''this module is an alternative way to call zonal_stats. The issue is that in ArcGIS 10, having zones too small to capture any cells
causes a crash in the entire interpreter (regardless of exception handling). So, we want to crash a separate interpreter, catch that crash, and proceed'''

import sys

import zonal_stats
import log # this will create some interesting issues in the log where it's adding a ton of new "runs"

import arcpy
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

zones = sys.argv[1] 
raster = sys.argv[2]
zone_field = sys.argv[3]

if len(sys.argv) > 4:
        filename = sys.argv[4]
else:
        filename = None
        
if len(sys.argv) > 5:
        output_location = sys.argv[5]
else:
        output_location = None

# this error checking isn't super substantive
if filename == "":
	filename = None
if output_location == "":
	output_location = None

if not zones or not raster or not zone_field:
	log.error("Can't run zonal_stats without zones, raster, and zone_field")
	sys.exit(1)

try:
	output_file = zonal_stats.zonal_stats(zones,raster,zone_field,filename,output_location,silent=True)
	print output_file # this should be different, but we want to make sure that only this makes it to stdout here
except:
        raise
	log.error("Interpreter crash - continuing")
	sys.exit(1) # exit with a failure

arcpy.CheckInExtension("Spatial")

sys.exit(0) # specify zero - it defaults here, but that's ok
