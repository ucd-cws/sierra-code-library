"""
	This tool is meant to be used as an arcgis 10.0 (or above) script tool. It takes a layer of huc 12s and checks
	the downstream attributes using a number of unit-test like functions to ensure that they meet all criteria that
	would make them a valid data layer.

	This tool was developed in a few stages, at first just as a script to paste into ArcMap 10's Python editor, and
	secondly as a standalone script tool. As a result, it contains some vestiges of its history and a few data structures
	are somewhat of duplicates - it shouldn't be a problem, but a future version should clean these up
"""

import traceback
import os
import sys

import arcpy

from code_library.common import log
from code_library.common import geospatial
from code_library.common import huc_network # need it for network_end_hucs

log.initialize(arc_script=True,html=True)

# primary parameters
layer = arcpy.GetParameterAsText(0)
method = arcpy.GetParameterAsText(1)
output_gdb = arcpy.GetParameterAsText(2)
output_filename = arcpy.GetParameterAsText(3)


key_field = arcpy.GetParameterAsText(4)
if not key_field:
	log.write("Setting key field to %s" % huc_network.zones_field)
	key_field = huc_network.zones_field

ds_field = arcpy.GetParameterAsText(5)
if not ds_field:
	log.write("Setting DS field to %s" % huc_network.ds_field)
	ds_field = huc_network.ds_field

hu10_key = "HUC_10" # basic definitions - not params
hu10_ds_key = "HU_10_DS"

### Some error checking
log.write("checking existence of input",level="debug")
if not arcpy.Exists(layer):
	log.error("Input layer doesn't exist. Problemo cowboy. Please specify some input features and make sure they exist.")
	sys.exit()

### Some definitions
huc12s_index = []
huc10s_index = []
marked_as_bad = []
watersheds = {}
issues_index = {}

reload_interval = 100 # specifies how often to reload the layer of zones as a feature Layer - # much higher than 100 can
					# lead to slowdowns and much lower may be unnecessary

class huc_issue:
	def __init__(self,huc_12 = None,reason = None,issue_notes = None,huc_10 = None, ds = None, ds10 = None):
		self.huc_12 = huc_12
		self.hu_12_ds = ds
		self.huc_10 = huc_10
		self.hu_10_ds = ds10
		self.reason = reason
		self.issue_notes = issue_notes

	def get_value(self,attribute):
		"""
		Returns the attribute of the object instance with the name specified

		:param attribute: the name of the attribute to retrieve
		:return: variable: defined by input
		:raise: AttributeError
		"""
		if hasattr(self,attribute):
			return str(self.__dict__[attribute])
		else:
			raise AttributeError("Attribute %s does not exist for huc_issue class" % attribute)

def check_huc_from_row(row):
	"""
	runs a series of checks on the attributes of each huc

	:param row:
	:return:
	"""

	global marked_as_bad
	global issues_index

	huc_12_id = row.getValue(key_field) # cache it - we'll use it a bunch right now
	huc_12_ds = row.getValue(ds_field)

	if not row.getValue(key_field):
		return 0

	if huc_12_ds not in huc12s_index and huc_12_ds not in huc_network.network_end_hucs:
		issue = huc_issue(huc_12_id,"ds_dne","Downstream HUC_12 does not exist in this dataset")
		marked_as_bad.append(issue)
		issues_index[huc_12_id].append(issue)

	if row.getValue(hu10_ds_key) not in huc10s_index and row.getValue(hu10_ds_key) not in huc_network.network_end_hucs:
		message = "Downstream HUC_10 does not exist in this dataset"
		reason = "10_ds_dne"

		issue = huc_issue(huc_12_id,reason,message,huc_10 = row.getValue(hu10_key))
		marked_as_bad.append(issue)
		issues_index[huc_12_id].append(issue)

	if row.getValue(hu10_key) not in huc_12_ds and row.getValue(hu10_ds_key) not in huc_12_ds:
		message = "Downstream HUC_12 is not within the current HUC_10 or the downstream HUC_10 - possible problem with any of those attributes"
		reason = "ds_not_within"

		issue = huc_issue(huc_12_id,reason,message,huc_10 = row.getValue(hu10_key))
		marked_as_bad.append(issue)
		issues_index[huc_12_id].append(issue)

def check_hucs(feature_class):

	zone_curs = arcpy.SearchCursor(feature_class)

	i = 0
	for row in zone_curs:
		i+=1
		if (i % 100) == 0: # if it's divisible by 100, report the number
			log.write("%s processed" % i, True)
		check_huc_from_row(row)

def reset_feature_layer(feature_class,layer_name = None):
	"""
		Remakes the feature layer for the given feature class and layer name.

		Arcpy selections tend to get slower as more of them are done, so remaking it periodically (~100 selections)
		greatly helps with speed

	:param feature_class: The feature class to make into a feature layer
	:param layer_name: The layer name to check
	:return: layer_name
	"""

	log.warning("Reloading zones_layer",False)

	try:
		if arcpy.Exists(layer_name):
			arcpy.Delete_management(layer_name)
	except:
		log.error("Had trouble deleting or detecting existence of feature layer. Proceeding, but the next step may fail")

	try:
		arcpy.MakeFeatureLayer_management(feature_class,layer_name)
	except:
		log.error("Couldn't create feature layer to check boundaries")
		raise

	return layer_name

def check_boundary_from_id(zone_id, feature_layer, zone_network, key_field, geospatial_obj):
	"""
	takes the huc, gets the huc 12, does a boundary touches new selection on the feature_layer - returns a huc_issue or True

	:param zone_id: the actual id of the zone we want to check (as defined in the key_field)
	:param feature_layer: the layer to use to check it against
	:param zone_network: A network of these zones as created by huc_network.setup_network
	:param key_field: The field that holds the ids
	:param geospatial_obj: Saves some time by performing a function once, then passing it into the select_hucs

	"""

	if not zone_id or not feature_layer or not zone_network:
		log.error("Missing parameters to check_boundary_from_id")
		raise ValueError("Missing parameters to check_boundary_from_id")

	if zone_network[zone_id].downstream in huc_network.network_end_hucs:
		# don't even run the test if it's a network end huc - just return True
		return True

	try:
		checked = huc_network.select_hucs([zone_id],feature_layer,copy_out=False,geospatial_obj=geospatial_obj)
	except:
		log.error("Couldn't select initial zone for boundary check. Zone ID = %s" % zone_id)
		raise

	if checked and checked is None:
		raise RuntimeError("Couldn't run boundary touches test")

	try:
		huc_network.grow_selection(feature_layer,feature_layer,copy_out=False)
	except:
		log.error("Couldn't grow selection for boundary check. Zone ID = %s" % zone_id)
		raise

	bound_curs = arcpy.SearchCursor(feature_layer)

	for row in bound_curs:
		if row.getValue(key_field) == zone_network[zone_id].downstream: # currently looked at zone == specified zone's ds? - ie, is the zone of interest's downstream in this set?
			return True # it's in it!
	else: # if we don't break/return, then it's not there. Return False
		return False


def check_boundaries(feature_class, key_list, zone_network, key_field):
	"""
	runs check boundary from row for everything else.

	:param feature_class: the input huc layer to check
	:return ?: TODO: Figure out if it returns something
	"""

	log.write("Checking boundaries",True)
	log.warning("This could take some time, depending on the number of zones you're checking and the beefiness of your computer. A good estimate is a few hours to many days. You may want to go get a cup of coffee, take a nap, or possibly go on vacation")

	log.write("Setting up the data file",level="debug")
	geospatial_obj = huc_network.setup_huc_obj(feature_class)

	i = 1

	feature_layer = reset_feature_layer(feature_class, "f_layer") # get it to start with

	for feature_id in key_list:
		if (i % 10) == 0:
			log.write(i,True)

		if (i % reload_interval) == 0:
			feature_layer = reset_feature_layer(feature_class, "f_layer")

		i+= 1

		try:
			ds_ok = check_boundary_from_id(feature_id,feature_layer,zone_network, key_field,geospatial_obj)

		except RuntimeError as e:
			issue = huc_issue(feature_id,"test_fail",str(e))
			marked_as_bad.append(issue)
			issues_index[feature_id].append(issue)
			break # break instead of continue - we don't want multiple errors and the results will be incomplete
		except:
			issue = huc_issue(feature_id,"test_fail","Couldn't run boundary touches check")
			marked_as_bad.append(issue)
			issues_index[feature_id].append(issue)
			break # break instead of continue - we don't want multiple errors and the results will be incomplete

		if not ds_ok:
			issue = huc_issue(feature_id,"ds_does_not_touch","The downstream zone does not touch this zone.",)
			marked_as_bad.append(issue)
			issues_index[feature_id].append(issue)

def load_features(feature_class):
	temp_features = geospatial.generate_fast_filename("huc_layer")
	try:
		arcpy.CopyFeatures_management(feature_class,temp_features)
	except:
		log.warning("Couldn't copy features to memory - trying to copy to disk")
		original_except = traceback.format_exc()
		try:
			temp_features= geospatial.generate_gdb_filename(return_full = True)
			arcpy.CopyFeatures_management(feature_class,temp_features)
		except:
			log.error("Can't make a copy of the features - %s" % original_except)
			raise
	log.write("Features copied to %s" % temp_features,True)
	return temp_features

def attach_errors(feature_class,issues,add_cols = (("error_reason_code","TEXT", "reason"),("description","TEXT","issue_notes"))):
	for column in add_cols:
		try:
			arcpy.AddField_management(feature_class,column[0],column[1],'','',65535)
		except:
			log.error("Couldn't create field with name %s on the output" % column[0])
			raise

	attach_curs = arcpy.UpdateCursor(feature_class)

	for row in attach_curs: # got hrough all the rows
		for col in add_cols: # go through the columns to attach and add them
			t_issues = issues[row.getValue(key_field)] # just to clean the code up  a bit = this retrieves the issues for this zone
			attach_str = ""
			for issue in t_issues:
				attach_str = "%s %s," % (attach_str,issue.get_value(col[2]))

			row.setValue(col[0],attach_str) # set the value on the field specified to the issue in the index's value of attribute specified in col[2]
			attach_curs.updateRow(row) # save it!


try:
	temp_features = load_features(layer)
except: # in this case everything is already printed out
	sys.exit()

try:
	watersheds = huc_network.setup_network(layer, layer, return_copy=True)
except:
	log.error("couldn't set up watershed network - can't proceed")
	raise

log.write("Indexing",True)
huc_curs = arcpy.SearchCursor(temp_features)	
for row in huc_curs:
	huc12s_index.append(row.getValue(key_field))
	huc10s_index.append(row.getValue(hu10_key))
	issues_index[row.getValue(key_field)] = [] # set this up for every huc
del huc_curs

log.write("Conducting Basic Check",True)
check_hucs(temp_features)
if method == "Thorough":
	log.write("Conducting Thorough Check", True)
	check_boundaries(temp_features,huc12s_index,watersheds,key_field)

# now copy the features out and add the errors

log.write("Attaching Information to Zones",True)
attach_errors(temp_features,issues_index,(("error_reason_code","TEXT", "reason"),("description","TEXT","issue_notes")))

log.write("Copying Out Layer",True)
out_name = arcpy.CreateUniqueName(output_filename,output_gdb) # make sure it's unique
full_out_path = os.path.join(output_gdb,out_name)

log.write("Output will go to %s" % full_out_path)
try:
	arcpy.CopyFeatures_management(temp_features,full_out_path)
except:
	log.error("Failed to copy features to output destination of %s. They still exist at %s though, so you can find them there, or in your arcmap window if you ran this tool from there" % (full_out_path,temp_features))
	full_out_path = temp_features # redirect the output path because we're about to use it to create the feature layer

# and then set the output
output_layer = out_name
try:
	arcpy.MakeFeatureLayer_management(full_out_path,output_layer)
except:
	log.error("Output layer name already exists OR not running in arcmap - output is at %s" % full_out_path)

log.write("\nLayer checked. Note that caught errors MAY NOT encompass all errors on the downstream attributes for this layer, but caught errors should find genuine issues. You should run this tool again after making any corrections as previously unreported issues may then be caught",True)
arcpy.SetParameter(6,output_layer)




