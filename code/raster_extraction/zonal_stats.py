import os
import tempfile

import arcpy
from arcpy import env
from arcpy.sa import *

from code_library.common import geospatial
import config
import support
import log


#old_vars = ["rch","aet","cwd","pet","snow","subl","stor"]
#all_vars = ["run","ppt","pck","tmax","tmin"]
# Check out the ArcGIS Spatial Analyst extension license

#raster_names = ["GFDL_A2","PCM_A2"]
#config_data_dir = os.path.join(os.getcwd(),"..","data_futures")

#inZoneData = os.path.join(os.getcwd(),"snmeadows_area.gdb","snmeadows_hucs")

def run_multi_zonal(zones_files,gdb,log_string = None,merge = False, zone_field = None):
	'''batches zonal stats across a set of rasters'''
	
	var_num = 0
	
	if zone_field:
		true_zone_field = zone_field
	else:
		true_zone_field = config.zone_field

	return_tables = [] # will become a list of lists unless merge is True, then it's just a list
	
	for raster in gdb.rasters:
		var_num += 1
		zone_num = 0
		
		log.write("Switching Vars to %s - # %s" % (raster,var_num),True)
		
		zs_list = []
		
		for zone_file in zones_files:
			
			zone_num += 1
			
			if log_string:
				log.write("\n%s; raster %s; feature %s" % (log_string,var_num,zone_num),True)
			else:
				log.write("\nraster %s; feature %s" % (var_num,zone_num),True)
			
			try:
				outfile = zonal_stats(zone_file,os.path.join(gdb.path,raster),true_zone_field)
				
				if outfile:
					zs_list.append(outfile)
			except:
				log.error("Failed to run zonal stats on raster %s in gdb %s" % (raster,gdb.name))
				continue
			
		if merge:
			output_name = raster
			output_merged = merge_zonal(zs_list,output_name)
			if output_merged:
				return_tables.append(output_merged)
		else:
			return_tables.append(zs_list)
	
	return return_tables

def merge_zonal(file_list,output_name):

	try:
		arcpy.Merge_management(file_list,output_name)
	except:
		log.error("Couldn't merge")
		return None
		
	return output_name

def zonal_stats(zones,raster,zone_field,filename = None, output_location = None):

	try:
		# Set local variables
		raster_name = os.path.splitext(os.path.split(raster)[1])[0]
		if filename is None or output_location is None:
			filename,output_location = geospatial.generate_gdb_filename("xt_%s" % raster_name)
			
		out_table = os.path.join(output_location,"%s" % (filename))

		try:
			if arcpy.Exists(out_table):
				log.write("Skipping - already complete",True)
				return out_table
		except:
			log.error("Couldn't test if it already exists...move along!")

		try:
			log.write("Running Zonal",True)
			outZSaT = ZonalStatisticsAsTable(zones, zone_field, raster, out_table, "DATA", "ALL")
		except SystemExit:
			log.error("System Exit returned from ZonalStatisticsAsTable")
		except:
			raise
			log.error("Unable to run stats on raster %s" % out_table)
			return None

		del outZSaT # these should be local, but it's Arc!
		
		return out_table
				
	except:
		raise
		log.error("Unhandled Exception in zonal_stats function")

