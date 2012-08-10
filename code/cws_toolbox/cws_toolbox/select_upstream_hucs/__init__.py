'''
Created on Apr 13, 2012

@author: nicksantos
'''
import time
import tempfile

import arcpy

from code_library.common import log # @UnresolvedImport

huc_to_find_upstream = arcpy.GetParameterAsText(0)
# other parameters to add
# zones_file - should be able to be a separate file from the selected
# DS Field

watersheds = {}
network_end_hucs = ["CLOSED BASIN","Mexico","OCEAN"]

number_selections = 0
number_selections_threshold = 450 # approximately aligns it with the cleanup for the FGDBs

zones_layer_name = None
zones_field = "HUC_12"
ds_field = "HU_12_DS"
zones_cleanup = False

huc_masks = {}

temp_folder = tempfile.mkdtemp(prefix = "select_hucs")
temp_gdb = arcpy.CreateFileGDB_management(temp_folder,"select_hucs_temp.gdb")

zones_file = None # will be defined by get_zones_file

log.init_log(arc_script = True)

def get_zones_file(input_file):
	'''takes a feature layer, and returns the path of the original file'''
	
	desc = arcpy.Describe(input_file)
	path = desc.catalogPath
	
	del desc
	
	return path

class watershed():
	def __init__(self):
		self.HUC_12 = None
		self.downstream = None
		self.upstream = None # actually [], but we want to check if it's defined
		self.has_dam = False
		
def setup_network(zones_layer = None):

	global watersheds
	
	zones_layer = check_zones(zones_layer,"setup_network")
		
	# some setup
	log.write("Setting up watershed network",True)
	reader = arcpy.SearchCursor(zones_layer)
	for record in reader:
		t_ws = watershed()
		t_ws.HUC_12 = record.getValue(zones_field)
		t_ws.downstream = record.getValue(ds_field)
		watersheds[record.HUC_12] = t_ws
		
	zones_layer = cleanup_zones(zones_layer,"setup_network")
	

def find_upstream(watershed,all_watersheds,dams_flag=False):
	
	#log.write("getting upstream watershed for %s" % watershed)

	if watershed in all_watersheds and all_watersheds[watershed].upstream: # if we've already run for this watershed
		print "already run upstream for %s" % (watershed)
		return all_watersheds[watershed].upstream
	
	if dams_flag and watershed.has_dam:
		return [] # if this is a dam and we're account for that, return nothing upstream - can't go further
	
	all_us = []
	for wat in all_watersheds.keys():
		if all_watersheds[wat].downstream == watershed:
			us = find_upstream(wat,all_watersheds,dams_flag)
			all_us.append(wat)
			all_us += us
	
	all_watersheds[watershed].upstream = all_us
	log.write("returning upstream for %s" % (watershed))
	return all_us

def get_hucs(feature,zone_layer=None):
	'''select huc by location and get the huc_12 id and return it'''
	
	log.write("Getting huc ids")

	zone_layer = check_zones(zone_layer,"get_hucs")
	
	arcpy.SelectLayerByLocation_management(zone_layer,"INTERSECT",feature,"","NEW_SELECTION")
	global number_selections
	number_selections += 1
	
	hucs = read_hucs(zone_layer)
	
	zone_layer = cleanup_zones(zone_layer,"get_hucs")
	
	return hucs

def read_hucs(zone_layer):
	t_curs = arcpy.SearchCursor(zone_layer)
	
	hucs = []
	for row in t_curs:
		hucs.append(row.getValue(zones_field))
		
	return hucs

def check_zones(zones_layer = None,cleanup = False):
	global zones_layer_name
	global zones_cleanup
	
	# if it is specified directly, return that
	if zones_layer:
		return zones_layer
	else:
		if zones_layer_name: # if we have the global layer - this should be most common
			return zones_layer_name
		else:
			zl = "tzl_check_zones"
			arcpy.MakeFeatureLayer_management(zones_file,zl)
			zones_layer_name = zl
			if not zones_cleanup: # if we don't already have a saved cleanup name
				zones_cleanup = cleanup # save the calling function's name here
			
			return zones_layer_name

def cleanup_zones(zones_layer,cleanup,allow_delete=False):
	global zones_cleanup
	global zones_layer_name
	global number_selections
	
	try:
		if zones_layer_name == zones_layer and zones_cleanup == cleanup:
			#log.write("Destroying Zones Layer",True)
			arcpy.Delete_management(zones_layer)
			zones_layer_name = None
			zones_cleanup = False
		elif number_selections > number_selections_threshold and allow_delete is True: # allow delete flags that we're between ops so we don't do it at a terrible time on accident
			
			# after running a bunch of selections, it gets slow, so destroy it and make a new one
			#log.write("Reloading Zones",True)
			arcpy.Delete_management(zones_layer)
			zones_layer_name = None
			number_selections = 0
			zones = check_zones(cleanup = cleanup)
	except:
		pass

def select_hucs(huc_list,zone_layer=None,copy_out = True):
	
	try:
		log.write("Selecting features")
		
		zone_layer = check_zones(zone_layer,"select_hucs")
		
		#log.write("Selecting HUCs")
		selection_type = "NEW_SELECTION" # start a new selection, then add to
		try:
			arcpy.SelectLayerByAttribute_management(zone_layer,"CLEAR_SELECTION") # we need to do this because if we don't then two layers in a row with the same number of records will result in the second (or third, etc) being skipped because the following line will return the selected number
			log.write("Selecting %s zones" % len(huc_list))
			zone_expression = "" # the where clause - we want to initialize it to blank
			for index in range(len(huc_list)): # we have to do this in a loop because building one query to make Arc do it for us produces an error
				zone_expression = zone_expression + "\"HUC_12\" = '%s' OR " % huc_list[index] # brackets are required by Arc for Personal Geodatabases and quotes for FGDBs (that's us!)
				if index % 25 == 0 or index == len(huc_list)-1: # Chunking: every nth HUC, we run the selection, OR when we've reached the last one. we're trying to chunk the expression. Arc won't take a big long one, but selecting 1 by 1 is slow
					zone_expression = zone_expression[:-4] # chop off the trailing " OR "
					arcpy.SelectLayerByAttribute_management(zone_layer,selection_type,zone_expression)
					selection_type = "ADD_TO_SELECTION" # set it so that selections accumulate
					zone_expression = "" # clear the expression for the next round
			
			global number_selections
			number_selections += 1
		except:
			
			cleanup_zones(zone_layer,"select_hucs")
			
			log.error("Couldn't select hucs")
			return None
		
		if copy_out: # if we're supposed to copy it out to a file - we might not need to because we might do something with the layer after this
			log.write("Copying out",True)
			t_name = arcpy.CreateUniqueName("upstream_hucs",temp_gdb)
			arcpy.CopyFeatures_management(zone_layer,t_name)
		
		cleanup_zones(zone_layer,"select_hucs")
		
	except:
		return None
	
	if copy_out:
		return t_name
	else:
		return None
	
def grow_selection(features,zones_layer):
	'''this function takes a selection of hucs and grows the selection to the immediately surrounding hucs
	so that when we delineate using this layer as a mask, we don't crop out anything important through
	misalignment'''
	
	if not zones_layer:
		return None
	
	try:
		global number_selections
		number_selections += 1
		
		#system.time_check("grow_selection_actual")
		arcpy.SelectLayerByLocation_management(zones_layer,"BOUNDARY_TOUCHES",features)
		#elapsed = system.time_report("grow_selection_actual")
		
		t_name = arcpy.CreateUniqueName("zones_extent_grow",temp_gdb)
		
		#system.time_check("copy_features")
		arcpy.CopyFeatures_management(zones_layer,t_name)
		#elapsed = system.time_report("copy_features")
		
		print "grew selection"
		
		return t_name
	except:
		return None
	
def get_mask(feature):
	'''given an input feature, it finds the full potential upstream area and returns a
	feature to use as an analysis mask to speed delineation'''
	
	print "getting analysis mask for feature"
	
	try:
		zones_layer = check_zones(cleanup="get_mask")

		hucs = get_hucs(feature,zones_layer) # get the initial hucs

		return get_upstream(hucs)
	except:
		log.error("analysis mask failed")
		return None

def get_upstream(hucs):
	try:
		log.write("Getting Upstream HUCs",True)
		hucs_to_select = list(set(hucs)) # we want a copy, might as well dedupe...
		
		main_huc = hucs[0]
		zones_layer = check_zones(cleanup="get_upstream")

		for huc in hucs:
			if huc in huc_masks.keys():
				log.write("short_circuiting")
				return huc_masks[huc] # short circuit!
			
			hucs_to_select += find_upstream(huc,watersheds) # add the upstream hucs to the list
		
		hucs_to_select = list(set(hucs_to_select)) # remove duplicates - it'll speed things up a bit!
		
		log.write("Selecting %s hucs" % len(hucs_to_select),True)
		
		if len(hucs_to_select) == 0: # it'll return the whole layer if we don't have anything, so just have it return None and we'll use the default masks
			return None
		
		extent_layer = select_hucs(hucs_to_select,zones_layer)

		cleanup_zones(zones_layer,"get_upstream",allow_delete=True)
		
		huc_masks[main_huc] = extent_layer # save it so we can short circuit next time!

		return extent_layer
	except:
		log.error("select upstream failed")
		return None
	
def get_upstream_from_hucs(hucs_layer):

	hucs = read_hucs(hucs_layer)
	
	layer = get_upstream(hucs)
	
	if layer:
		arcpy.SetParameter(1,layer)
	else:
		log.error("No Layer to Return")

zones_file = get_zones_file(huc_to_find_upstream)
log.write("Using %s for zones_file" % zones_file,True)
setup_network()
get_upstream_from_hucs(huc_to_find_upstream)