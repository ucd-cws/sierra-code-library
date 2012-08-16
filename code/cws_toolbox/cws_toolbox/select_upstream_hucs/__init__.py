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
in_zones_file = arcpy.GetParameterAsText(2)
in_huc_field = arcpy.GetParameterAsText(3)
in_ds_field = arcpy.GetParameterAsText(4)
# other parameters to add
# zones_file - should be able to be a separate file from the selected
# DS Field

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
		upstream_layer = network.get_upstream_from_hucs(huc_to_find_upstream)
	
		if upstream_layer:
			arcpy.SetParameter(5,upstream_layer)
		else:
			log.error("No Upstream Layer to Return")
			
	if direction == "Downstream" or direction == "Both":
		downstream_layer = network.get_downstream_from_hucs(huc_to_find_upstream)
	
		if downstream_layer:
			arcpy.SetParameter(6,downstream_layer)
		else:
			log.error("No Downstream Layer to Return")
except:
	error_str = traceback.format_exc()
	log.error(error_str)