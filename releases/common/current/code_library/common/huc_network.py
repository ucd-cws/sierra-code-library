'''as is common, much of this code would be better in a class/object form. It is currently a refactoring of existing code, so this is far
progressed from the initial implementation. A future version might include a class-based implementation'''

import tempfile
import traceback
import sys

import arcpy

from code_library.common import log #@UnresolvedImport
from code_library.common import geospatial #@UnresolvedImport

number_selections = 0
number_selections_threshold = 450 # approximately aligns it with the cleanup for the FGDBs

config_selection_chunk_size = 25 # how many hucs should we select in each chunk? Higher is faster, but may run up against arc's limits

zones_layer_name = None
zones_field = "HUC_12"
ds_field = "HU_12_DS"
zones_cleanup = False

zones_file = None # will be defined by get_zones_file

watersheds = {}
network_end_hucs = ["CLOSED BASIN","Mexico","OCEAN","MEXICO","Closed Basin","Ocean","CLOSED BAS"] # CLOSED BAS is for HUC10s. The shorter field size truncates the statement

huc_layer_cache = None # scripts will need to intialize this to {}

temp_folder = None
temp_gdb = None

class watershed():
	def __init__(self):
		self.HUC_12 = None
		self.downstream = None
		self.upstream = None # actually [], but we want to check if it's defined
		self.has_dam = False
		
def setup_network(in_zones_file = None, zones_layer = None, return_copy = False):

	global watersheds,temp_folder,temp_gdb
	
	temp_folder = tempfile.mkdtemp(prefix = "select_hucs")
	temp_gdb = arcpy.CreateFileGDB_management(temp_folder,"select_hucs_temp.gdb")

	log.warning("Warning: Setting system recursion limit to a high number")
	sys.setrecursionlimit(6000) # cover a reasonably large huc network
	
	if in_zones_file:
		global zones_file
		zones_file = in_zones_file
	if not zones_file:
		log.error("No zones_file specified for module to run on - can't run without zones_file")
		return False
	
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

	if return_copy:
		return watersheds
	else:
		return True

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
	
	del row
	del t_curs
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
			log.write("Destroying Zones Layer")
			arcpy.Delete_management(zones_layer)
			zones_layer_name = None
			zones_cleanup = False
		elif number_selections > number_selections_threshold and allow_delete is True: # allow delete flags that we're between ops so we don't do it at a terrible time on accident
			
			# after running a bunch of selections, it gets slow, so destroy it and make a new one
			log.write("Reloading Zones")
			arcpy.Delete_management(zones_layer)
			zones_layer_name = None
			number_selections = 0
			zones = check_zones(cleanup = cleanup)
	except:
		pass

def setup_huc_obj(zone_layer):

	desc = arcpy.Describe(zone_layer)
	huc_layer_obj = geospatial.data_file(desc.path)
	check = huc_layer_obj.set_delimiters()

	del desc

	if check is False:
		log.error("Couldn't determine type of storage or unsupported storage type for file. Can't set up huc network.")
		cleanup_zones(zone_layer,"select_hucs")
		return False

	return huc_layer_obj

def select_hucs(huc_list,zone_layer=None,copy_out = True, base_name = "hucs",geospatial_obj = None):
	
	try:
		log.write("Selecting features")
		
		zone_layer = check_zones(zone_layer,"select_hucs")
		
		if not geospatial_obj:
			huc_layer_obj = setup_huc_obj(zone_layer)
			if huc_layer_obj is False:
				return False
		else:
			huc_layer_obj = geospatial_obj
			log.write("using passed in geospatial_obj",level="debug")

		#log.write("Selecting HUCs")
		selection_type = "NEW_SELECTION" # start a new selection, then add to
		try:
			arcpy.SelectLayerByAttribute_management(zone_layer,"CLEAR_SELECTION") # we need to do this because if we don't then two layers in a row with the same number of records will result in the second (or third, etc) being skipped because the following line will return the selected number
			log.write("Selecting %s zones" % len(huc_list))
			zone_expression = "" # the where clause - we want to initialize it to blank
			for index in range(len(huc_list)): # we have to do this in a loop because building one query to make Arc do it for us produces an error
				zone_expression = zone_expression + "%s%s%s = '%s' OR " % (huc_layer_obj.delim_open,zones_field,huc_layer_obj.delim_close,huc_list[index]) # brackets are required by Arc for Personal Geodatabases and quotes for FGDBs (that's us!)
				if index % config_selection_chunk_size == 0 or index == len(huc_list)-1: # Chunking: every nth HUC, we run the selection, OR when we've reached the last one. we're trying to chunk the expression. Arc won't take a big long one, but selecting 1 by 1 is slow
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
			t_name = arcpy.CreateUniqueName(base_name,temp_gdb)
			arcpy.CopyFeatures_management(zone_layer,t_name)
			log.write("Saved to %s" % t_name, True)
		
		cleanup_zones(zone_layer,"select_hucs")
		
	except:
		return None
	
	if copy_out:
		return t_name
	else:
		return None
	
def grow_selection(features,zones_layer,output_name = None,copy_out=True):
	"""
	this function takes a selection of hucs and grows the selection to the immediately surrounding hucs
	so that when we delineate using this layer as a mask, we don't crop out anything important through
	misalignment

	:param features: selection features
	:param zones_layer: features to select
	:param output_name: Optional. If no output name is supplied, one will be generated
	"""
	
	if not zones_layer:
		return None
	
	try:
		global number_selections
		number_selections += 1
		
		#system.time_check("grow_selection_actual")
		arcpy.SelectLayerByLocation_management(zones_layer,"BOUNDARY_TOUCHES",features)
		#elapsed = system.time_report("grow_selection_actual")

		log.write("grew_selection")

		if copy_out:
			if output_name:
				t_name = output_name # if a name is passed in, use it instead
			else:
				t_name = arcpy.CreateUniqueName("zones_extent_grow",temp_gdb)

			#system.time_check("copy_features")
			arcpy.CopyFeatures_management(zones_layer,t_name)
			#elapsed = system.time_report("copy_features")

			log.write("Saved selection",level="debug")

			return t_name

	except:
		return None

	return None # if we get here, return None
	
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

def get_upstream(hucs, include_initial = True):
	"""
	given a list of HUCs as a starting point, selects all upstream HUCs and returns them as a feature layer

	:param hucs: list. the huc or hucs to get the upstream of.
	:param include_initial: Boolean. Indicates whether the starting hucs should be included in the returned layer. Default
	is True
	:return:
	"""

	try:
		log.write("Getting Upstream HUCs",True)
		hucs_to_select = list(set(hucs)) # we want a copy, might as well dedupe...
		
		main_huc = hucs[0]
		zones_layer = check_zones(cleanup="get_upstream")

		for huc in hucs:
			if huc_layer_cache and huc in huc_layer_cache.keys():# huc layer cache stores the layers that are generated. Some scripts will use it when they use this function multiple times.
				log.write("short_circuiting")
				return huc_layer_cache[huc] # short circuit!

			hucs_to_select += find_upstream(huc,watersheds) # add the upstream hucs to the list

		if include_initial:
			hucs_to_select = list(set(hucs_to_select)) # remove duplicates - it'll speed things up a bit!
		else: # we don't want to include the intial hucs
			hucs_to_select = list(set(hucs_to_select) - set(hucs)) # so subtract the set of initial hucs from the current set.

		log.write("Selecting %s hucs" % len(hucs_to_select),True)
		
		if len(hucs_to_select) == 0: # it'll return the whole layer if we don't have anything, so just have it return None and we'll use the default masks
			return None
		
		extent_layer = select_hucs(hucs_to_select,zones_layer,base_name="upstream_hucs")

		cleanup_zones(zones_layer,"get_upstream",allow_delete=True)

		if huc_layer_cache:
			huc_layer_cache[main_huc] = extent_layer # save it so we can short circuit next time!

		return extent_layer
	except:
		error_string = traceback.format_exc()
		log.error("select upstream failed\n%s" % error_string)
		return None

def get_downstream(hucs, include_initial = True):
	
	log.write("Getting Downstream HUCs",True)
	
	try:
		zones_layer = check_zones(cleanup="get_downstream")
		
		hucs_to_select = []
		for huc in hucs:
			hucs_to_select += get_downstream_path(huc,watersheds)
		
		log.write("Selecting %s hucs" % len(hucs_to_select),True)
		
		if len(hucs_to_select) == 0: # it'll return the whole layer if we don't have anything, so just have it return None and we'll use the default masks
			return None

		if include_initial is False:
			hucs_to_select = list(set(hucs_to_select) - set(hucs)) # subtract the initial hucs back out
		
		extent_layer = select_hucs(hucs_to_select,zones_layer,base_name="downstream_hucs")
		
		cleanup_zones(zones_layer,"get_downstream",allow_delete=True)
	
		return extent_layer

	except:
		error_string = traceback.format_exc()
		log.error("select downstream failed\n%s" % error_string)
		return None
	
def get_downstream_path(zone,l_watersheds):
	"""
		starts with a huc and uses the watershed network to find a path downstream
	"""

	current_DS = zone # set the starting huc
	path_list = []
	while (current_DS is not None): # basically, run forever. We'll manually break
		
		try:
			if current_DS in network_end_hucs: # we've reached the end!
				break
			if current_DS in path_list: # oh shit, we're in an infinite loop! better warn the user and break
				log.warning("Infinite loop in network. A downstream huc references an upstream huc. %s is part of this loop - check its 'upstream hucs'" % current_DS)
				break
			path_list.append(current_DS) # otherwise, add this item to the list of hucs in the path
			try:
				current_DS = l_watersheds[current_DS].downstream # then set the current item to this one's downstream item
			except KeyError: # we have hucs that reference downstream hucs, but because we clip to CA, they are missing - we need to tolerate that
				break
		except:
			log.error("Error finding downstream path. Path is likely incomplete")
			break
		
	return path_list

def get_upstream_from_hucs(hucs_layer,dissolve_flag = False,include_initial=True):

	hucs = read_hucs(hucs_layer)
	
	upstream_layer = get_upstream(hucs,include_initial)

	if dissolve_flag:
		log.write("Dissolving",True)
		return geospatial.fast_dissolve(upstream_layer,raise_error=False,base_name="dissolved_upstream_hucs")
	else:
		return upstream_layer


def get_downstream_from_hucs(hucs_layer,dissolve_flag = False,include_initial=True):
	hucs = read_hucs(hucs_layer)
	
	downstream_layer = get_downstream(hucs,include_initial)

	if dissolve_flag:
		log.write("Dissolving",True)
		return geospatial.fast_dissolve(downstream_layer,raise_error=False,base_name="dissolved_downstream_hucs")
	else:
		return downstream_layer