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

base_map = arcpy.GetParameterAsText(0) # the map definition that we want to use as the basis w/queries
queries = arcpy.GetParameterAsText(1) # semicolon separated - per ArcGIS. the stack of queries from a map - might be a duplicate, depending on the UI - if we want users to add/remove queries in the tool, then not a dupe.
bind_values = arcpy.GetParameter(3) # semicolon separated - per ArcGIS.  the bind values as - need to be split
return_layers = [] # the layers that will be returned back to arcgis

# 1) Can select entire map and have the queries filled in...

# 2) Dropdown fills in select box (like the NADconverter) with queries
# 3) if custom, read custom box
# 4) comma separated bind variables for *each* query
# 5-12) 8 return options - returns empty layer (or nothing?) if nothing.