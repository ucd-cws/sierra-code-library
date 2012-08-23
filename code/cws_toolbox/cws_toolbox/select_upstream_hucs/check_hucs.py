import traceback
import os
import sys

import arcpy

from code_library.common import log
from code_library.common import geospatial
from code_library.common import network # need it for network_end_hucs

log.init(arc_script=True,html=True)

layer = arcpy.GetParameterAsText(0)
method = arcpy.GetParameterAsText(1)
output_gdb = arcpy.GetParameterAsText(2)

if not arcpy.Exists(layer):
	log.error("Input layer doesn't exist. Problemo cowboy. Please specify some input features and make sure they exist.")

huc12s_index = []
huc10s_index = []
marked_as_bad = []

class huc_issue:
	def __init__(self,huc_12 = None,reason = None,issue_notes = None,huc_10 = None, ds = None, ds10 = None):
		self.huc_12 = huc_12
		self.hu_12_ds = ds
		self.huc_10 = huc_10
		self.hu_10_ds = ds10
		'''items are lists because a huc can end up here for multiple reasons'''
		self.reason = [reason]
		self.issue_notes = [issue_notes]

issues_index = {}

def check_huc_from_row(row):
	global marked_as_bad
	global issues_index
	
	'''runs a series of checks on the attributes of each huc'''
	huc_12_id = row.getValue("HUC_12") # cache it - we'll use it a bunch right now
	huc_12_ds = row.getValue("HU_12_DS")
	
	if not row.getValue("HUC_12"):
		return 0
	
	if huc_12_ds not in huc12s_index and huc_12_ds not in network.network_end_hucs:
		issue = huc_issue(huc_12_id,"ds_dne","Downstream HUC_12 does not exist in this dataset")
		marked_as_bad.append(issue)
		issues_index[huc_12_id] = issue
		
	if row.getValue("HU_10_DS") not in huc10s_index and row.getValue("HU_10_DS") not in network.network_end_hucs:
		message = "Downstream HUC_10 does not exist in this dataset"
		reason = "10_ds_dne"
		
		if huc_12_id in issues_index:
			issues_index[huc_12_id].reason.append(reason)
			issues_index[huc_12_id].issue_notes.append(message)
		else:
			issue = huc_issue(huc_12_id,reason,message,huc_10 = row.getValue("HUC_10"))
			marked_as_bad.append(issue)
			issues_index[huc_12_id] = issue
		
	if row.getValue("HUC_10") not in huc_12_ds and row.getValue("HU_10_DS") not in huc_12_ds:
		message = "Downstream HUC_12 is not within the current HUC_10 or the downstream HUC_10 - possible problem with nay of thos attributes"
		reason = "ds_not_within"
		
		if huc_12_id in issues_index:
			issues_index[huc_12_id].reason.append(reason)
			issues_index[huc_12_id].issue_notes.append(message)
		else:
			issue = huc_issue(huc_12_id,reason,message,huc_10 = row.getValue("HUC_10"))
			marked_as_bad.append(issue)
			issues_index[huc_12_id] = issue

def check_hucs(feature_class):
	pass

def check_boundary_from_row(row, feature_layer):
	'''takes the huc, gets the huc 12, does a boundary touches new selection on the feature_layer - returns a huc_issue or True''' 

def check_boundaries(feature_class):
	'''runs check boundary from row for everything else.'''
	pass

def load_features(feature_class):
	temp_features = "in_memory/huc_layer"
	try:
		arcpy.Copy_management(feature_class,temp_features)
	except:
		log.warning("Couldn't copy features to memory - trying to copy to disk")
		original_except = traceback.format_exc()
		try:
			temp_features= geospatial.generate_gdb_filename(return_full = True)
			arcpy.Copy_management(feature_class,temp_features)
		except:
			log.error("Cant's make a copy of the features - %s" % original_except)
			sys.exit()
	log.write("Features copied",True)
	return temp_features


temp_features = load_features(layer)

huc_curs = arcpy.SearchCursor(temp_features)	
for row in huc_curs:
	huc12s_index.append(row.getValue("HUC_12"))
	huc10s_index.append(row.getValue("HUC_10"))
del huc_curs
	
check_hucs(temp_features)
if method == "Thorough":
	check_boundaries(temp_features)

# now copy the features out

# and then set the output
arcpy.SetParameter(3,output_layer)

		
	
		
