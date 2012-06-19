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
	
	log.init_log(config.run_dir)
	
	arcpy.CheckOutExtension("Spatial")
	
	for ds in config.current_datasets.keys():
		tds = raster_dataset(ds,os.path.join(config.data_folder,config.current_datasets[ds]))
		config.datasets.append(tds)
		config.datasets_index[ds] = tds
		
	if not arcpy.Exists(input_dataset):
		log.error("Input dataset does not exist. Exiting")
		sys.exit()

def split_items(features,gdb,feature_type = "POLYGON"):
	'''this could probably be done with an arcgis function - realized after writing...'''
	
	log.write("Splitting features",True)
	
	features_name = os.path.splitext(os.path.split(features)[1])[0]
	
	desc = arcpy.Describe(features)
	
	has_id_col = None
	if desc.hasOID:
		has_id_col = True
		id_col = desc.OIDFieldName
	else:
		id_col = 0
	
	all_features = arcpy.SearchCursor(features)		
	
	arcpy.MakeFeatureLayer_management(features,"t_features") # make it a feature layer so we can use it as a template
	
	tid = 0
	
	split_features = []
	
	for feature in all_features:
		if has_id_col:
			tid = feature.getValue(id_col)
		else:
			tid += 1		
		
		feature_filename = "%s_%s_" % (features_name,tid)
		
		t_name = arcpy.CreateUniqueName(feature_filename,gdb)
		t_name_parts = os.path.split(t_name) # split it back out to feed into the next function
		log.write("splitting out to %s" % t_name)
		
		# make a new feature class
		arcpy.CreateFeatureclass_management(t_name_parts[0],t_name_parts[1],feature_type,"t_features","DISABLED","DISABLED",desc.spatialReference)
		ins_curs = arcpy.InsertCursor(t_name)
		
		# copy this feature into it
		t_row = ins_curs.newRow()
		for field in desc.fields: # copy each field
			try:
				if field.editable:
					t_row.setValue(field.name,feature.getValue(field.name))
			except:
				log.write("skipping col %s - can't copy" % field.name,False,"debug")
				continue
		
		t_row.shape = feature.shape # copy the shape over explicitly

		ins_curs.insertRow(t_row)
		
		split_features.append(t_name)
		
		try:
			del ins_curs # close the cursor
		except:
			continue
				
	del desc # kill the describe object
	arcpy.Delete_management("t_features") # delete the feature layer
	
	return split_features


def run_files(filenames,datasets):
	'''splits the file into pieces and runs each gdb for it'''
	
	if check_gdb(config.run_dir, "temp.gdb"):
		file_db = os.path.join(config.run_dir, "temp.gdb")
	else:
		log.error("No temp db and can't create, exiting")
	
	num_files = len(filenames)
	file_num = 0
	for filename in filenames:
		file_num += 1
		
		all_features = split_items(filename,file_db)
		num_features = len(all_features)
		
		filename_unique = os.path.splitext(os.path.split(filename)[1])[0] # not so unique except that it's meant for creating a unique gdb for each zones/variable set
		
		feature_num = 0
				
		for dataset in datasets:
			
			for feature in all_features:
				feature_num += 1
				feature_string = "File %s of %s; feature %s of %s" % (file_num,num_files,feature_num,num_features)
				
				zonal_stats.run_zonal(feature,dataset.gdbs,dataset.name,filename_unique,feature_string)

def run_join(filenames,datasets):
	
	for dataset in datasets:
		join_tables.join(dataset.zonal_stats_files,config.zone_field,config.field_names)
		