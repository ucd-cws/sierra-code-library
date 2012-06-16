import os
import sys

import arcpy

import log
import config

class raster_dataset:
	def __init__(self, name = None, folder = None):
		self.name = name
		self.folder = folder
		self.gdbs = []
				
		temp_gdbs = arcpy.ListWorkspaces(self.folder)
		for db in temp_gdbs:
			self.gdbs.append(raster_gdb(db))
		
class raster_gdb:
	def __init__(self,path):
		self.rasters = arcpy.ListRasters(path)
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
	
def setup():
	
	arcpy.CheckOutExtension("Spatial")
	
	for ds in config.current_datasets.keys():
		log.write("Setting up dataset %s" % ds)
		tds = raster_dataset(ds,config.current_datasets[ds])
		config.datasets.append(tds)
		config.datasets_index[ds] = tds
		
	if not arcpy.Exists(config.input_dataset):
		log.error("Input dataset does not exist. Exiting")
		sys.exit()

def run_file(filename):
	'''splits the file into pieces and runs each gdb for it'''
	
	file_db = check_gdb(config.run_dir, "temp.gdb")
	
	
	pass