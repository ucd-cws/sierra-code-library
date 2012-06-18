import os
import sys

import arcpy

import log
import config
import zonal_stats

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
	
	arcpy.CheckOutExtension("Spatial")
	
	for ds in config.current_datasets.keys():
		tds = raster_dataset(ds,os.path.join(config.data_folder,config.current_datasets[ds]))
		config.datasets.append(tds)
		config.datasets_index[ds] = tds
		
	if not arcpy.Exists(input_dataset):
		log.error("Input dataset does not exist. Exiting")
		sys.exit()

def run_files(filenames,datasets):
	'''splits the file into pieces and runs each gdb for it'''
	
	#file_db = check_gdb(config.run_dir, "temp.gdb")
	for filename in filenames:
		for dataset in datasets:
			zonal_stats.run_zonal(filename,dataset.gdbs,dataset.name)
	