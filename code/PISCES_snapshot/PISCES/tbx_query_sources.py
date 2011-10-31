'''provides an entry point for these functions from an ArcGIS 10 Toolbox'''

import arcpy
import vars, funcs, log

try:
    from _winreg import *
    registry = ConnectRegistry("",HKEY_CURRENT_USER) # open the registry
    base_folder = QueryValue(registry,"Software\CWS\PISCES\location") # get the PISCES location
    CloseKey(registry)
except:
    log.error("Unable to get base folder")
    sys.exit()


vars.set_workspace_vars(base_folder) # set up the workspace to the location

import script_tool_funcs
base_folder = script_tool_funcs.get_location()

log.initialize("opening for tbx_query_sources.py",arc_script = 1)

layer = arcpy.GetParameterAsText(0)
species = arcpy.GetParameterAsText(1)

species = script_tool_funcs.parse_input_species_from_list(species) # parse out the species code
zones = script_tool_funcs.zones_feature_to_array(layer)

db_cursor,db_conn = funcs.db_connect(vars.maindb, "Connecting to database to get source data for zones")

script_tool_funcs.query_datasets_by_zone(zones,db_conn,species)

funcs.db_close(db_cursor,db_conn)