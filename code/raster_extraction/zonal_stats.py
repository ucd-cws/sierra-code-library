import os

import arcpy
from arcpy import env
from arcpy.sa import *

import config
import support
import log
import processify
	

#old_vars = ["rch","aet","cwd","pet","snow","subl","stor"]
#all_vars = ["run","ppt","pck","tmax","tmin"]
# Check out the ArcGIS Spatial Analyst extension license

#raster_names = ["GFDL_A2","PCM_A2"]
#config_data_dir = os.path.join(os.getcwd(),"..","data_futures")

#inZoneData = os.path.join(os.getcwd(),"snmeadows_area.gdb","snmeadows_hucs")

def run_zonal(zones_file,gdbs,dataset_name,unique_filename,feature_string = None):
	'''batches zonal stats across a set of rasters'''
	
	var_num = 0
	
	return_tables = [] # will become a list of lists
	for gdb in gdbs:
		var_num += 1
		num_processed = 0   
		log.write("Switching Vars to %s - # %s" % (gdb.name,var_num),True)

		# Set environment settings
		arcpy.env.workspace = os.path.join(config.data_folder,dataset_name,gdb.name)

		filename = os.path.splitext(os.path.split(zones_file)[1])[0]

		out_workspace = os.path.join(config.output_folder,"zonal_%s_%s.gdb" % (unique_filename,gdb.name))
		if support.check_gdb(config.output_folder,"zonal_%s_%s.gdb" % (unique_filename,gdb.name)) is False:
			log.error("setting up db for %s failed" % out_workspace)
			continue
		
		file_list = []
		
		for raster in gdb.rasters:
			if feature_string:
				log.write("\n%s; var %s -- %s already processed" % (feature_string,var_num,num_processed),True)
			else:
				log.write("\nvar %s -- %s already processed" % (var_num,num_processed),True)
			num_processed += 1
		
			log.write("processing %s" % raster,True)

			try:
				outfile = zonal_stats(zones_file,filename,os.path.join(gdb.path,raster),out_workspace,config.zone_field)
				
				if outfile:
					file_list.append(outfile)
			except:
				raise
				log.error("Failed to run zonal stats on raster %s in gdb %s" % (raster,gdb.name))
				continue
		
		return_tables.append(file_list)


def multifile_zonal(files,filename,raster,zone_field,output_location,merge_flag = False):
	# very broken
	
	results = []
	for t_file in files:
		results.append(zonal_stats(t_file,filename,os.path.join(gdb.path,raster),out_workspace,config.zone_field))
		

#@processify.processify
def zonal_stats(zones,filename,raster,output_location,zone_field):

	try:
		# Set local variables
		raster_name = os.path.splitext(os.path.split(raster)[1])[0]
		out_table = os.path.join(output_location,"%s_%s" % (filename,raster_name))

		try:
			if arcpy.Exists(out_table):
				log.write("Skipping - already complete")
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

