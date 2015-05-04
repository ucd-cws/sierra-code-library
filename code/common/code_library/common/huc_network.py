'''as is common, much of this code would be better in a class/object form. It is currently a refactoring of existing code, so this is far
progressed from the initial implementation. A future version might include a class-based implementation'''

import tempfile
import traceback
import sys
import csv
import os

import arcpy

from code_library.common import log
from code_library.common import geospatial

short_circuit = True  # configures whether when finding upstream hucs, we should allow short circuiting for speed
short_circuit_warning = False  # have we shown the warning yet?

number_selections = 0
number_selections_threshold = 450  # approximately aligns it with the cleanup for the FGDBs

config_selection_chunk_size = 200  # how many hucs should we select in each chunk? Higher is faster, but may run up against arc's limits

zones_layer_name = None
zones_field = "HUC_12"
ds_field = "HU_12_DS"
pkey_field = "OBJECTID"
zones_cleanup = False

zones_file = None  # will be defined by get_zones_file

watersheds = {}
network_end_hucs = ["CLOSED BASIN", "Mexico", "OCEAN", "MEXICO", "Closed Basin", "Ocean", "CLOSED BAS"]  # CLOSED BAS is for HUC10s. The shorter field size truncates the statement
direct_upstream = {}  # keyed on HUC12s and each key has a list of the huc12s that feed into it - helps to speed creation of network later by not going through the whole thing many times

huc_layer_cache = None  # scripts will need to intialize this to {}

temp_folder = None
temp_gdb = None


class watershed():
	def __init__(self):
		self.zone_id = None
		self.downstream = None
		self.upstream = None  # actually [], but we want to check if it's defined - NOT automatically populated by setup_network unless "populate_upstream" is True
		self.has_dam = False
		self.pkey = None

		self.downstream_obj = None  # an object version of the DS huc

	def to_csv(self, path=None, rows_only=False):
		header_row = ["HUC12", "Upstream HUC12s"]
		out_rows = [header_row, [self.zone_id] + self.upstream]  # make the object and add the first row
		for ws in self.upstream:
			out_rows.append([watersheds[ws].zone_id] + watersheds[ws].upstream)

		if rows_only:
			return out_rows
		else:
			if not path:
				raise ValueError("Parameter 'path' to method 'to_csv' is required when directly outputting a CSV")

			file_handle = open(path, 'wb')
			file_writer = csv.writer(file_handle)
			file_writer.writerows(out_rows)
			return True


def setup_network(in_zones_file=None, zones_layer=None, return_copy=False, pkey_as_dict_key=False, populate_upstream=False):

	global watersheds, direct_upstream, temp_folder, temp_gdb
	watersheds = {}  # reset these in the event that we run it multiple times in a script
	direct_upstream = {}

	temp_folder = tempfile.mkdtemp(prefix="select_hucs")
	temp_gdb = arcpy.CreateFileGDB_management(temp_folder, "select_hucs_temp.gdb")

	log.warning("Warning: Setting system recursion limit to a high number")
	sys.setrecursionlimit(6000)  # cover a reasonably large huc network
	
	if in_zones_file:
		global zones_file
		zones_file = in_zones_file
	if not zones_file:
		log.error("No zones_file specified for module to run on - can't run without zones_file")
		return False
	
	zones_layer = check_zones(zones_layer, "setup_network")
		
	# some setup
	log.write("Setting up watershed network", True)
	reader = arcpy.SearchCursor(zones_layer)
	for record in reader:
		t_ws = watershed()
		t_ws.zone_id = record.getValue(zones_field)
		t_ws.downstream = record.getValue(ds_field)
		t_ws.pkey = record.getValue(pkey_field)

		if pkey_as_dict_key:  # we might want to index based upon the pkey
			watersheds[t_ws.pkey] = t_ws
		else:  # otherwise, the default is to index by HUC12
			watersheds[record.getValue(zones_field)] = t_ws

		if t_ws.downstream in direct_upstream:  # if the downstream huc is already in the network listing
			direct_upstream[t_ws.downstream].append(t_ws.zone_id)  # just append the current HUC12
		else:
			direct_upstream[t_ws.downstream] = [t_ws.zone_id, ]  # otherwise, create a list with this item in it

		if not t_ws.zone_id in direct_upstream:  # then check here so that everything gets added, including watersheds with nothing feeding into them
			direct_upstream[t_ws.zone_id] = []

	for wid in watersheds:  # add a reference to the downstream object into the object
		if watersheds[wid].downstream in network_end_hucs:
			watersheds[wid].downstream_obj = None
			continue
		if watersheds[wid].downstream in watersheds:  # otherwise, so long as the downstream object exists
			watersheds[wid].downstream_obj = watersheds[watersheds[wid].downstream]

	if populate_upstream:  # if we want it to automatically populate the upstream field
		for ws in watersheds:
			watersheds[ws].upstream = find_upstream(ws, watersheds)


	zones_layer = cleanup_zones(zones_layer,"setup_network")

	if return_copy:
		return watersheds
	else:
		return True


def find_upstream(l_watershed, all_watersheds, dams_flag=False, include_self=False):
	
	#log.write("getting upstream watershed for %s" % l_watershed)

	global short_circuit_warning

	if short_circuit and l_watershed in all_watersheds and all_watersheds[l_watershed].upstream:  # if we've already run for this watershed
		if include_self and not short_circuit_warning:
			log.warning("Short circuiting is enabled, but include_self is not its default value. If you mix values for include_self in the same program, you'll get incorrect results. Set huc_network.short_circuit to False or only use a single value for include_self")
			short_circuit_warning = True
		log.write("already run upstream for %s" % l_watershed)
		return all_watersheds[l_watershed].upstream
	
	if dams_flag and l_watershed.has_dam:
		return []  # if this is a dam and we're account for that, return nothing upstream - can't go further

	if include_self:
		all_us = [l_watershed, ]
	else:
		all_us = []

	for watershed_string in direct_upstream[l_watershed]:  # look at all the hucs directly upstream of this
		us = find_upstream(watershed_string, all_watersheds, dams_flag, include_self=include_self)  # find what's upstream of them
		if not include_self:  # if it's not supposed to add itself, then add the upstream watershed here. If it's going to include itself, then that will get added when find_upstream is run for it, so we don't need to do this
			all_us.append(watershed_string)
		all_us += us  # then add what's upstream of them
	
	all_watersheds[l_watershed].upstream = all_us
	#log.write("returning upstream for %s" % (l_watershed))
	return all_us


def get_hucs(feature, zone_layer=None):
	'''select huc by location and get the huc_12 id and return it'''
	
	log.write("Getting huc ids")

	zone_layer = check_zones(zone_layer, "get_hucs")
	
	arcpy.SelectLayerByLocation_management(zone_layer, "INTERSECT", feature, "", "NEW_SELECTION")
	global number_selections
	number_selections += 1
	
	hucs = read_hucs(zone_layer)
	
	zone_layer = cleanup_zones(zone_layer, "get_hucs")
	
	return hucs


def read_hucs(zone_layer):
	t_curs = arcpy.SearchCursor(zone_layer)
	
	hucs = []
	for row in t_curs:
		huc_value = row.getValue(zones_field)
		if not huc_value:  # skip it if it's None
			continue
		hucs.append(huc_value)
	
	del row
	del t_curs
	return hucs


def find_outlets(zones_list):
	if len(watersheds.keys()) == 0:
		raise ValueError("watersheds object has not been set up. Please run setup_network first")

	root_items = []
	for zone in zones_list:
		for other_zone in zones_list:
			if other_zone == zone:
				continue
			if zone in watersheds[other_zone].upstream:  # if zone is upstream of any element here, break, skipping the else/append
				break
		else:
			root_items.append(zone)  # if we didn't break (ie, if this zone isn't upstream of any others), then this will run
	return root_items


def make_upstream_csv(hucs, output_csv):
	outlet_hucs = find_outlets(hucs)  # remove any hucs that are upstream of other hucs

	csv_rows = []
	for huc in outlet_hucs:
		csv_rows += watersheds[huc].to_csv(path=None, rows_only=True)

	output_path = os.path.join(output_csv, "huc_network_output.csv")

	file_handle = open(output_path, 'wb')
	file_writer = csv.writer(file_handle)
	file_writer.writerows(csv_rows)
	file_handle.close()


def make_upstream_matrix(hucs, output_csv, include_self_flag=False, zones_name="HUC_12"):

	csv_rows = []
	header_row = [zones_name]

	if include_self_flag:  # if the option to include_self earlier was used, then don't add the current hucs back in here
		list_comp = [t_us for t_huc in hucs for t_us in watersheds[t_huc].upstream]
	else:
		list_comp = [t_us for t_huc in hucs for t_us in watersheds[t_huc].upstream] + hucs

	for huc in list_comp:  # list comprehension merges all of the hucs in the upstream lists for every huc in the initial list with the hucs themselves so that we get one master list of all hucs that need to be in the matrix
		out_dict = {zones_name: huc}
		for upstream in watersheds[huc].upstream:  # add it to the dict
			out_dict[upstream] = 1

			if not upstream in header_row:  # check the header to make sure it's there
				header_row.append(upstream)
		csv_rows.append(out_dict)

	output_path = os.path.join(output_csv, "huc_connectivity_matrix.csv")

	log.write("Output path: %s" % output_path, True)
	file_handle = open(output_path, 'wb')
	file_writer = csv.DictWriter(file_handle, header_row)
	file_writer.writeheader()
	file_writer.writerows(csv_rows)
	file_handle.close()


def check_zones(zones_layer=None, cleanup=None):
	global zones_layer_name
	global zones_cleanup
	
	# if it is specified directly, return that
	if zones_layer:
		return zones_layer
	else:
		if zones_layer_name:  # if we have the global layer - this should be most common
			return zones_layer_name
		else:
			zl = "tzl_check_zones"
			arcpy.MakeFeatureLayer_management(zones_file, zl)
			zones_layer_name = zl
			if not zones_cleanup:  # if we don't already have a saved cleanup name
				zones_cleanup = cleanup  # save the calling function's name here
			
			return zones_layer_name

def cleanup_zones(zones_layer, cleanup, allow_delete=False):
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


def select_hucs(huc_list, zone_layer=None, copy_out=True, base_name="hucs", geospatial_obj = None):
	
	try:
		log.write("Selecting features")
		
		zone_layer = check_zones(zone_layer,"select_hucs")
		
		if not geospatial_obj:
			huc_layer_obj = setup_huc_obj(zone_layer)
			if huc_layer_obj is False:
				return False
		else:
			huc_layer_obj = geospatial_obj
			log.write("using passed in geospatial_obj", level="debug")

		selection_type = "NEW_SELECTION"  # start a new selection, then add to
		try:
			arcpy.SelectLayerByAttribute_management(zone_layer, "CLEAR_SELECTION") # we need to do this because if we don't then two layers in a row with the same number of records will result in the second (or third, etc) being skipped because the following line will return the selected number
			log.write("Selecting %s zones" % len(huc_list))
			zone_expression = ""  # the where clause - we want to initialize it to blank
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

	return None  # if we get here, return None
	
def get_mask(feature):
	'''given an input feature, it finds the full potential upstream area and returns a
	feature to use as an analysis mask to speed delineation'''
	
	print "getting analysis mask for feature"
	
	try:
		zones_layer = check_zones(cleanup="get_mask")

		hucs = get_hucs(feature, zones_layer)  # get the initial hucs

		return get_upstream(hucs)
	except:
		log.error("analysis mask failed")
		return None

def get_upstream(hucs, include_initial=True, include_self=False):
	"""
	given a list of HUCs as a starting point, selects all upstream HUCs and returns them as a feature layer

	:param hucs: list. the huc or hucs to get the upstream of.
	:param include_initial: Boolean. Indicates whether the starting hucs should be included in the returned layer. Default
	is True
	:return:
	"""

	try:
		log.write("Getting Upstream HUCs", True)
		hucs_to_select = list(set(hucs))  # we want a copy, might as well dedupe...
		
		main_huc = hucs[0]
		zones_layer = check_zones(cleanup="get_upstream")

		for huc in hucs:
			if huc_layer_cache and huc in huc_layer_cache.keys():  # huc layer cache stores the layers that are generated. Some scripts will use it when they use this function multiple times.
				return huc_layer_cache[huc]  # short circuit!

			hucs_to_select += find_upstream(huc, watersheds, include_self=include_self)  # add the upstream hucs to the list

		if include_initial or include_self:
			hucs_to_select = list(set(hucs_to_select))  # remove duplicates - it'll speed things up a bit!
		else:  # we don't want to include the initial hucs
			hucs_to_select = list(set(hucs_to_select) - set(hucs))  # so subtract the set of initial hucs from the current set.

		log.write("Selecting %s hucs" % len(hucs_to_select), True)
		
		if len(hucs_to_select) == 0:  # it'll return the whole layer if we don't have anything, so just have it return None and we'll use the default masks
			return None
		
		extent_layer = select_hucs(hucs_to_select, zones_layer, base_name="upstream_hucs")

		cleanup_zones(zones_layer, "get_upstream", allow_delete=True)

		if huc_layer_cache:
			huc_layer_cache[main_huc] = extent_layer  # save it so we can short circuit next time!

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
		
		extent_layer = select_hucs(hucs_to_select, zones_layer, base_name="downstream_hucs")
		
		cleanup_zones(zones_layer, "get_downstream", allow_delete=True)
	
		return extent_layer

	except:
		error_string = traceback.format_exc()
		log.error("select downstream failed\n%s" % error_string)
		return None


def get_downstream_path(zone, l_watersheds):
	"""
		starts with a huc and uses the watershed network to find a path downstream
	"""

	current_DS = zone  # set the starting huc
	path_list = []
	while current_DS is not None:  # basically, run forever. We'll manually break
		
		try:
			if current_DS in network_end_hucs:  # we've reached the end!
				break
			if current_DS in path_list:  # oh shit, we're in an infinite loop! better warn the user and break
				log.warning("Infinite loop in network. A downstream huc references an upstream huc. %s is part of this loop - check its 'upstream hucs'" % current_DS)
				break
			path_list.append(current_DS)  # otherwise, add this item to the list of hucs in the path
			try:
				current_DS = l_watersheds[current_DS].downstream # then set the current item to this one's downstream item
			except KeyError:  # we have hucs that reference downstream hucs, but because we clip to CA, they are missing - we need to tolerate that
				break
		except:
			log.error("Error finding downstream path. Path is likely incomplete")
			break
		
	return path_list


def get_upstream_from_hucs(hucs_layer, dissolve_flag=False, include_initial=True, upstream_of_self=False):

	hucs = read_hucs(hucs_layer)
	
	upstream_layer = get_upstream(hucs, include_initial, include_self=upstream_of_self)

	if dissolve_flag:
		log.write("Dissolving", True)
		return geospatial.fast_dissolve(upstream_layer, raise_error=False, base_name="dissolved_upstream_hucs")
	else:
		return upstream_layer


def get_downstream_from_hucs(hucs_layer, dissolve_flag=False, include_initial=True):
	hucs = read_hucs(hucs_layer)
	
	downstream_layer = get_downstream(hucs, include_initial)

	if dissolve_flag:
		log.write("Dissolving", True)
		return geospatial.fast_dissolve(downstream_layer, raise_error=False, base_name="dissolved_downstream_hucs")
	else:
		return downstream_layer


def add_downstream_objectid_field(hucs_layer, objectid_field="OBJECTID"):
	global pkey_field

	pkey_field = objectid_field

	log.write("Setting up network", True)
	hucs = setup_network(hucs_layer, return_copy=True)

	log.write("Restructuring data", True)
	ds_dict = {}
	for wid in hucs:  # hucs is a dict
		#print "HUC %s" % wid
		#print "HUC %s has pkey %s" % (wid, hucs[wid].pkey)
		if not hucs[wid].downstream_obj:  # if we don't have a downstream obj
			ds_dict[hucs[wid].pkey] = None
		else:
			ds_dict[hucs[wid].pkey] = hucs[wid].downstream_obj.pkey

	log.write("Adding output field", True)
	arcpy.AddField_management(hucs_layer, "DS_OBJECTID", "LONG")
	log.write("Writing data out", True)
	geospatial.write_column_by_key(hucs_layer, "DS_OBJECTID", objectid_field, ds_dict)

	log.write("Done", True)