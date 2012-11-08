'''
Created on Apr 13, 2012

@author: nicksantos
'''
import time
import tempfile
import traceback
import sys
import re

import arcpy

from code_library.common import log # @UnresolvedImport
from code_library.common import huc_network as network #@UnresolvedImport

huc_to_find_upstream = arcpy.GetParameterAsText(0)
direction = arcpy.GetParameterAsText(1)
dissolve_output = arcpy.GetParameter(2)
include_selected = arcpy.GetParameter(3)
in_zones_file = arcpy.GetParameterAsText(4)
in_huc_field = arcpy.GetParameterAsText(5)
in_ds_field = arcpy.GetParameterAsText(6)
# other parameters to add

if dissolve_output is True or dissolve_output is False:
	dissolve_flag = dissolve_output
else:
	dissolve_flag = False

zones_file = None

log.init_log(arc_script = True)

def get_zones_file(input_file):
	'''takes a feature layer, and returns the path of the original file'''
	
	desc = arcpy.Describe(input_file)
	path = desc.catalogPath
	
	del desc
	
	return path

def handle_params(l_hucs_to_find_upstream,l_in_zones_file,l_in_huc_field,l_in_ds_field):
	if l_in_huc_field:
		network.zones_field = l_in_huc_field
	if l_in_ds_field:
		network.ds_field = l_in_ds_field
	
	if l_in_zones_file:
		return l_in_zones_file
	else:
		return get_zones_file(l_hucs_to_find_upstream)


zones_file = handle_params(huc_to_find_upstream,in_zones_file,in_huc_field,in_ds_field)
if not zones_file or not arcpy.Exists(zones_file):
	log.error("No zones file!")
	sys.exit()
	
log.write("Using %s for zones_file" % zones_file,True)

check = network.setup_network(in_zones_file = zones_file)
if not check: # error message already printed
	sys.exit()

try:
	if direction == "Upstream" or direction == "Both":
		upstream_layer = network.get_upstream_from_hucs(huc_to_find_upstream,dissolve_output,include_selected)
	
		if upstream_layer:
			arcpy.SetParameter(7,upstream_layer)
		else:
			log.error("No Upstream Layer to Return")
			
	if direction == "Downstream" or direction == "Both":
		downstream_layer = network.get_downstream_from_hucs(huc_to_find_upstream,dissolve_output,include_selected)
	
		if downstream_layer:
			arcpy.SetParameter(8,downstream_layer)
		else:
			log.error("No Downstream Layer to Return")
except:
	error_str = traceback.format_exc()
	log.error(error_str)