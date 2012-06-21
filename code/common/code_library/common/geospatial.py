'''
Created on Jun 20, 2012

@author: Nick
'''

import tempfile
import os
import sys

import arcpy

temp_folder = None
temp_gdb = None
raster_count = 0

try:
	import log
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

def generate_gdb_filename(name_base = "xt"):
	temp_gdb = get_temp_gdb()
	filename = arcpy.CreateUniqueName("name_base",temp_gdb)
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