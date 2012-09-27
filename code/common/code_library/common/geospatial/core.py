'''
Created on Aug 28, 2012

@author: nicksantos
'''

import tempfile
import os
import sys
import re
import traceback

import arcpy

import code_library #@UnresolvedImport

coordinate_systems = os.path.join(arcpy.GetInstallInfo()['InstallDir'],"Coordinate Systems")
projected_coordinate_systems = os.path.join(coordinate_systems,"Projected Coordinate Systems")
teale_albers = os.path.join(projected_coordinate_systems,"State Systems","NAD 1983 California (Teale) Albers (Meters).prj")

temp_folder = None
temp_gdb = None
raster_count = 0

delims_open = {'mdb':"[",'gdb':"\"",'shp':"\"",'in_memory':""} # a dictionary of field delimiters for use in sql statements. We don't always know that the huc layer will be stored
delims_close = {'mdb':"]",'gdb':"\"",'shp':"\"",'in_memory':""} # in one type of field or another. These two are just extension based lookups

try:
	from code_library.common import log #@UnresolvedImport
except:
	pass # fail silently - this will only be used in projects that have a log module 

class geospatial_object:
	
	def setup_object(self):
		'''like __init__ but won't be overridden by subclasses'''
		
		if 'setup_run' in self.__dict__: # check if we have this key in a safe way
			if self.setup_run is True: # have we already run this function
				return # don't run it again
		
		self.setup_run = True
		self.gdb = None
		self.temp_folder = None
		self.temp_gdb = None
	
	def check_temp(self):
		self.setup_object()
		
		
		if not self.temp_folder or not self.temp_gdb:
			try:
				self.temp_folder = tempfile.mkdtemp()
				temp_gdb = os.path.join(self.temp_folder,"join_temp.gdb")
				if arcpy.Exists(temp_gdb):
					self.temp_gdb = temp_gdb
				else: # doesn't exist
					if 'log' in sys.modules:
						log.write("Creating %s" % temp_gdb,True)
					arcpy.CreateFileGDB_management(self.temp_folder,"join_temp.gdb")
					self.temp_gdb = temp_gdb
			except:
				return False
		return True
	
	def get_temp_folder(self):
		self.setup_object()
		
		if self.check_temp():
			return self.temp_folder
		else:
			raise IOError("Couldn't create temp folder")
		
	def get_temp_gdb(self):
		self.setup_object()
		
		if self.check_temp():
			return self.temp_gdb
		else:
			raise IOError("Couldn't create temp gdb or folder")
		
	def split_items(self, features, gdb = None, feature_type = "POLYGON"):
		'''this could probably be done with an arcgis function - realized after writing...'''
		
		self.setup_object()
		
		if self.gdb is None:
			self.gdb = self.get_temp_gdb()
		
		if features is None: # use the instance's main file if the arg is none - it's not the default because eclipse was complaining about using "self" as an arg - may be possible, but haven't tested.
			features = self.main_file
		
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
			
			t_name = arcpy.CreateUniqueName(feature_filename,self.gdb)
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

class data_file(geospatial_object):
	def __init__(self,filename = None):
		self.data_location = filename
		
	def set_delimiters(self):
		
		try:
			fc_info = arcpy.ParseTableName(self.data_location)
			database, owner, featureclass = fc_info.split(",")
		except:
			log.error("Failed to assess data format")
			return False
		
		log.write("Type from ParseTableName = %s" % featureclass, level="debug")
		
		if re.match(" mdb",featureclass) is not None:
			self.delim_open = delims_open['mdb']
			self.delim_close = delims_close['mdb']
		elif re.match(" gdb",featureclass) is not None:
			self.delim_open = delims_open['gdb']
			self.delim_close = delims_close['gdb']
		elif re.match(" shp",featureclass) is not None:
			self.delim_open = delims_open['shp']
			self.delim_close = delims_close['shp']
		elif re.match(" in_memory",featureclass) is not None: # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = delims_open['in_memory']
			self.delim_close = delims_close['in_memory']
		elif re.match(" sde",featureclass) is not None: # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = ""
			self.delim_close = ""
		else:
			log.warning("No field delimiters for this type of data. We can select features in gdbs, mdbs, shps, in_memory, and possibly sde files (untested)",True)
			return False
		
		return True

def generate_fast_filename(name_base = "xt",return_full = True):
	'''uses the in_memory workspace and calls generate_gdb_filename with that as the gdb'''
	
	return generate_gdb_filename(name_base,return_full,"in_memory")

def generate_gdb_filename(name_base = "xt",return_full = True,gdb=None):
	'''returns the filename and the gdb separately for use in some tools'''
	if gdb is None:
		temp_gdb = get_temp_gdb()
	else:
		temp_gdb = gdb
		
	try:
		filename = arcpy.CreateUniqueName(name_base,temp_gdb)
	except:
		log.error("Couln't create GDB filename - %s" % traceback.format_exc())
		raise
	
	code_library.temp_datasets.append(filename) # add it to the tempfile registry
	
	if return_full:
		return filename
	else:
		return os.path.split(filename)[1],temp_gdb

def make_temp():

	global temp_gdb
	global temp_folder
	global raster_count
	
	if temp_gdb and raster_count < 100:
		raster_count += 1
		return temp_folder,temp_gdb
	else:
		raster_count = 0
	
	try:
		temp_folder = tempfile.mkdtemp()
		temp_gdb = os.path.join(temp_folder,"temp.gdb")
		if not arcpy.Exists(temp_gdb):
			if 'log' in sys.modules:
				log.write("Creating %s" % temp_gdb,True)
			arcpy.CreateFileGDB_management(temp_folder,"temp.gdb")
			return temp_folder,temp_gdb
	except:
		return False, False

def get_temp_folder():
	temp_folder,temp_gdb = make_temp()
	if temp_folder:
		return temp_folder
	else:
		raise IOError("Couldn't create temp gdb or folder")
	
def get_temp_gdb():
	
	temp_folder,temp_gdb = make_temp()
	if temp_gdb:
		return temp_gdb
	else:
		raise IOError("Couldn't create temp gdb or folder")

def check_spatial_filename(filename = None, create_filename = True, check_exists = True,allow_fast = False):
	'''usage: filename = check_spatial_filename(filename = None, create_filename = True, check_exists = True). Checks that we have a filename, optionally creates one, makes paths absolute,
		and ensures that they don't exist yet when passed in. Caller may disable the check_exists (for speed) using check_exists = False
	'''
	
	if not filename and create_filename is True:
		# if they didn't provide a filename and we're supposed to make one, then make one
		if allow_fast:
			return generate_fast_filename(return_full=True)
		else:
			return generate_gdb_filename(return_full=True)
	elif not filename:
		log.warning("No filename to check provided, but create_filename is False")
		return False
	
	if os.path.isabs(filename):
		rel_path = filename
		filename = os.path.abspath(filename)
		log.warning("Transforming relative path %s to absolute path %s" % (rel_path,filename))

	if check_exists and arcpy.Exists(filename):
		log.warning("Filename cannot already exist - found in check_spatial_filename")
		return False
		
	return filename

def get_spatial_reference(dataset = None):
	if not dataset:
		raise ValueError("No dataset provided to get spatial reference")
	
	desc = arcpy.Describe(dataset)
	
	sr = desc.spatialReference
	del desc
	
	return sr
