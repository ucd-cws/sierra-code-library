import vars
import arcpy

''' set of functions meant for use in ArcGIS Script Tools '''

'''def run_query(l_query,db_conn,bind_vars):'''
'''Given a query from a script tool, this runs it, and returns the results, if any. To be used as the base of other tools'''
'''
    db_cursor = db_conn.cursor()
    
    if len(bind_vars) > 0:
        l_results = db
    
    pass'''

def get_location():
    try:
        from _winreg import *
        registry = ConnectRegistry("",HKEY_CURRENT_USER) # open the registry
        base_folder = QueryValue(registry,"Software\CWS\PISCES\location") # get the PISCES location
        CloseKey(registry)
    except:
        log.error("Unable to get base folder")
        sys.exit()
    
    
    vars.set_workspace_vars(base_folder) # set up the workspace to the location
    
    return base_folder

def zones_feature_to_array(zones_layer):
    l_cursor = arcpy.SearchCursor(zones_layer)

    zones_array = []

    for feature in l_cursor: # should only iterate over the selected features
        zones_array.append(feature.HUC_12) # TODO: Fix HUC_12 Hardcode 
        
    return zones_array

def query_datasets_by_zone(zones, db_conn, species=None):
    
    db_cursor = db_conn.cursor()
    
    if not (type(zones) is tuple or type(zones) is list):
        zones = [zones] # make it into a list so that the same code works

    species_ext = ""    
    if species is not None:
        species_ext = " and t1.Species_ID = '%s'" % species
    
    query = "select distinct t1.Set_ID, t2.Source_Data, t2.Input_Filter from Observations as t1, Observation_Sets as t2 where t1.Zone_ID = ? and t1.Set_ID = t2.Set_ID%s" % species_ext
    arcpy.AddMessage("Running query - %s" % query)
    observation_sets = {}
    hucs = {}
    tablerows_by_source = []
    
    #TODO: Fix this block - it's probably broken
    for zone in zones:
        l_results = db_cursor.execute(query, zone)
        for result in l_results:
            if not (observation_sets.has_key(result.Set_ID)):
                observation_sets[result.Set_ID] = vars.observation_set()
                observation_sets[result.Set_ID].zones = [] # initialize an empty array of zones
                observation_sets[result.Set_ID].dataset_path = result.Source_Data # set the attributes
                observation_sets[result.Set_ID].Filter_Code = result.Input_Filter
            if not zone in observation_sets[result.Set_ID].zones: # if it's not already in there - though it shouldn't be...
                observation_sets[result.Set_ID].zones.append(zone) # add it
                tablerows_by_source.append(html_add_tablerow([result.Set_ID,result.Input_Filter,result.Source_Data,zone])) # store a table row to print to the final file
            
            arcpy.AddMessage("%s - %s - %s - %s" % (result.Set_ID,result.Input_Filter,result.Source_Data,zone)) # and print it directly to the arcpy console

    import os    
    l_out_filename = os.path.join(vars.internal_workspace,"log","query_datasets_by_zone_out.htm")
    
    if os.path.exists(l_out_filename):
        os.remove(l_out_filename) # get rid of the old file
    
    zone_out = open(l_out_filename,'a') # and open a new one
    
    zone_out.write("<html><body><h1>%s Source information</h1><table cellspacing=\"10\">" % species) # make a rudimentary non-standards-compliant html page
    for row in tablerows_by_source:
        zone_out.write(row)
    
    zone_out.write("</table></body></html>")
    
    arcpy.AddWarning("Full output is located at %s" % l_out_filename)
    
    #TODO: Make display better and highlight/note HUCs with multiple sources
    
    db_cursor.close()

def parse_input_species_from_list(l_search_species):
    '''takes a species from an ArcGIS 10 Script tool dropdown in the form of "Code - Common Name" and parses out the code and returns it'''

    import re
    
    species_re = re.search("^(\w{3}\d{2})",l_search_species)
    try:
        species = species_re.group(0)
    except:
        return None # if it didn't work, we probably don't have a species
    
    return species

def html_add_tablerow(items):
    l_row = "<tr>\n"
    for item in items:
        l_row = "%s<td>%s</td>\n" % (l_row,item) # add a table cell for the item
    l_row = "%s\n</tr>" % l_row # end the row
    
    return l_row
    