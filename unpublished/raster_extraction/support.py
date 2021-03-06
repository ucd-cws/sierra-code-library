'''
	This code ended up as some seriously bad spaghetti code. I tried to undo some of the damage when it became unwieldy, but it might have been too late.
	I apologize for the poor design decisions if you are looking at this code in order to maintain it.
	-Nick 6/20/2012

'''

import os
import sys

import arcpy

import log
import config
import zonal_stats
import join_tables
from code_library.common import geospatial
from code_library.common.geospatial import geometry

class raster_dataset:
	def __init__(self, name = None, folder = None):
		log.write("Setting up dataset %s" % name)
		self.name = name
		self.folder = folder
		self.gdbs = []
				
		arcpy.env.workspace = self.folder
		temp_gdbs = arcpy.ListWorkspaces()
		for db in temp_gdbs:
			self.gdbs.append(raster_gdb(db))
		
class raster_gdb:
	def __init__(self,path):
		log.write("Reading gdb at %s" % path,True)
		arcpy.env.workspace = path
		self.rasters = arcpy.ListRasters()
		self.zonal_stats_files = []
		self.name = os.path.splitext(os.path.split(path)[1])[0]
		self.path = path
		arcpy.env.workspace = None # prevent weird errors from leaving a "random" workspace

		self.output_gdb = os.path.join(config.output_folder,self.name) + ".gdb"
		if not arcpy.Exists(self.output_gdb):
			arcpy.CreateFileGDB_management(config.output_folder,self.name)

class polygon_file(geospatial.geospatial_object):
	def __init__(self, main_file):
		self.main_file = main_file
		self.split_files = self.split_items(self.main_file)
		self.length = len(self.split_files) # this is untrustworthy if anyone ever modifies self.split_files. But this shouldn't be used for anything important
											# just to save a few cycles if we're just printing out the number of polys

def check_gdb(folder,gdb_name):
	if not arcpy.Exists(os.path.join(folder,gdb_name)):
		try:
			log.write("Creating %s" % gdb_name,True)
			arcpy.CreateFileGDB_management(folder,gdb_name)
		except:
			file_failed(gdb_name,"Unable to create output geodatabase, and it doesn't exist - skipping entire variable!")
			return False
	return True

def file_failed(filename,msg):
	global error_log
	
	global flag_errors
	
	flag_errors = True
	log.error("Failed to process file: %s - %s" % (filename,msg))
	
	log.write(msg,True)
	
def setup(input_dataset):
	
	log.init_log(config.run_dir)
	
	arcpy.CheckOutExtension("Spatial")
	
	arcpy.env.overwriteOutput = True
	log.write("WARNING: Turning on overwrite output",True)
	
	for ds in config.current_datasets.keys():
		tds = raster_dataset(ds,os.path.join(config.data_folder,config.current_datasets[ds]))
		config.datasets.append(tds)
		config.datasets_index[ds] = tds
		
	if not arcpy.Exists(input_dataset):
		log.error("Input dataset does not exist. Exiting")
		sys.exit()
		
	if config.check_zone_size:
		log.warning("WARNING: check_zone_size is set to True. If your data is not all in the same units (as in, your catchments and your rasters should all be in meters, or some standard unit), things WILL BREAK. Either project your data, or set this flag to False in config.")

	if config.use_point_estimate:
		log.warning("CRITICAL WARNING: use_point_estimate is True. Your zone_field should NOT be the primary key (OID) field in this case or problems will occur. No checking will occur.")
		
def run_files(file_objects,datasets):
	'''splits the file into pieces and runs each gdb for it'''
	
	if check_gdb(config.run_dir, "temp.gdb"):
		file_db = os.path.join(config.run_dir, "temp.gdb")
	else:
		log.error("No temp db and can't create, exiting")
	
	num_files = len(file_objects)

	final_tables = []
	for dataset in datasets:
		gdb_num = 0
		num_gdbs = len(dataset.gdbs)
		for gdb in dataset.gdbs:
			gdb_num += 1
			file_num = 0
			for file_obj in file_objects:
			
				file_num += 1
				#feature_num += 1
				#feature_string = "File %s of %s; feature %s of %s" % (file_num,num_files,feature_num,num_features)
				
				log_string = "file %s of %s; gdb %s of %s" % (file_num,num_files,gdb_num,num_gdbs)
				
				# the below takes a list of files and a list of rasters and runs the files for each raster, returning a list of tables with the same name as the rasters
				final_tables.append(zonal_stats.run_multi_zonal(file_obj.split_files,gdb,log_string,merge = True))

	return final_tables

def run_join(filenames,datasets):
	
	for dataset in datasets:
		join_tables.join(dataset.zonal_stats_files,config.zone_field,config.field_names)


def point_estimate(zone_file,raster_gdbs):
	"""
	Handles the calling and management of obtaining a zonal-stats like table from a point estimate of a polygon
	:rtype : str
	"""

	raster_stack = make_raster_stack(raster_gdbs)

	log.write("Getting Centroids",True)
	point_objects = geometry.get_centroids_as_file(zone_file,dissolve=False)
	log.write("Centroid file located at %s" % point_objects,True)


	log.write("Getting Point Estimate",True)
	# modifies the input data
	i = 0
	num_ras = len(raster_stack)
	for raster in raster_stack:
		i += 1
		log.write("Raster %s/%s" % (i,num_ras),True)
		try:
			log.write("Operation 1/2",True)
			# first, copy it out - if it crashes, we don't want to ruin the whole set - we want to be able to move on.
			new_name = geospatial.generate_gdb_filename("point_est")
			arcpy.CopyFeatures_management(point_objects,new_name)
			point_objects = new_name
		except:
			log.warning("Failed to copy out points. Not critical unless a crash occurs during this next update")

		try:
			log.write("Operation 2/2",True)
			arcpy.sa.ExtractMultiValuesToPoints(point_objects,[raster],"NONE")
		except:
			log.warning("Failed to update points with values for raster %s. Continuing" % raster)

	log.write("Output is at %s" % point_objects, True)

	return point_objects

def make_raster_stack(datasets = []):

	log.write("Collapsing rasters into single stack")
	rasters = []

	for dataset in datasets:
		for gdb in dataset.gdbs:
			for raster in gdb.rasters:
				rasters.append(os.path.join(gdb.path,raster))

	return rasters