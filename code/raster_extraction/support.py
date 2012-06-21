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
from code_library.common import geospatial

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
	
	for ds in config.current_datasets.keys():
		tds = raster_dataset(ds,os.path.join(config.data_folder,config.current_datasets[ds]))
		config.datasets.append(tds)
		config.datasets_index[ds] = tds
		
	if not arcpy.Exists(input_dataset):
		log.error("Input dataset does not exist. Exiting")
		sys.exit()
		
def run_files(file_objects,datasets):
	'''splits the file into pieces and runs each gdb for it'''
	
	if check_gdb(config.run_dir, "temp.gdb"):
		file_db = os.path.join(config.run_dir, "temp.gdb")
	else:
		log.error("No temp db and can't create, exiting")
	
	num_files = len(file_objects)
	
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
				final_tables = zonal_stats.run_multi_zonal(file_obj.split_files,gdb,log_string,merge = True)

	return final_tables

def run_join(filenames,datasets):
	
	for dataset in datasets:
		join_tables.join(dataset.zonal_stats_files,config.zone_field,config.field_names)
		