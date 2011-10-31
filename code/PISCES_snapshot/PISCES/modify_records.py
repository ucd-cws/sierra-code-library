import arcpy, os, sys
import vars, args, log
import funcs
import re
import pyodbc
import script_tool_funcs

'''This script is meant to be run only as an ArcGIS script tool - messages will be passed out using arcpy'''

print "This script should only be run as an ArcGIS script tool. If you can see this message, you should exit or you better know what you are doing"

#set up the workspace


try:
    from _winreg import *
    registry = ConnectRegistry("",HKEY_CURRENT_USER) # open the registry
    base_folder = QueryValue(registry,"Software\CWS\PISCES\location") # get the PISCES location
    CloseKey(registry)
except:
    log.error("Unable to get base folder")
    sys.exit()


vars.set_workspace_vars(base_folder) # set up the workspace to the location
log.initialize("opening for modify_records.py",arc_script = 1)
#args.check_args()

# general
layer = arcpy.GetParameterAsText(0)
species = arcpy.GetParameterAsText(1)
operation = arcpy.GetParameterAsText(2) # add, remove, transfer
new_species = arcpy.GetParameterAsText(3)
reason_message = arcpy.GetParameterAsText(4)
where_string = arcpy.GetParameterAsText(5)

# for adding new records
default_input_filter = arcpy.GetParameterAsText(6)
default_observation_set = arcpy.GetParameterAsText(7)

update_range = arcpy.GetParameterAsText(8)

# do a sanity check
if arcpy.GetCount_management(layer).getOutput(0) == arcpy.GetCount_management(vars.HUCS).getOutput(0): # if we have all of the HUCs selected
    arcpy.AddError("Whoa - are you trying to destroy a whole species here? You selected the whole state! Since it was probably an error, we're going to just exit the program right now. If you intended to run that operation, do us a favor and select all of the polygons, then deselect just one so we know you are in your right mind. Then try again.")
    sys.exit()



if default_input_filter == None: # if one wasn't specified
    default_input_filter = "MKS" 

if species == None and new_species == None:
    log.error("No species to work on, exiting")
    sys.exit()

# TODO: Code exists for the following block in script_tool_funcs.py as parse_input_species_from_list()
species_re = re.search("^(\w{3}\d{2})",species) 
species = species_re.group(0)
if len(new_species) > 0:
    species_re = re.search("^(\w{3}\d{2})",new_species)
    new_species = species_re.group(0)
log.error("[%s]" % new_species)

log.write("Making changes to species %s" % species)
    
db_cursor,db_conn = funcs.db_connect(vars.maindb, "Connecting to database to modify HUC data")

def get_zones(layer,zones_array,column):
    
    dataset = arcpy.SearchCursor(layer)
    for row in dataset:
        zones_array.append(row.getValue(column)) #append the zones id to the array

def get_obs_set_id():
       
    select_string = "select Set_ID from Observation_Sets where Input_Filter = ?" # will select the first one
    results = db_cursor.execute(select_string,default_input_filter)
    
    for row in results: # return the first one we get
        return row.Set_ID

def get_defaults():
    if default_observation_set == "auto" or default_observation_set == None:
        set_id = get_obs_set_id()
    
    select_string = "select IFM.OBJECTID, IFM.Default_Observation_Type, IFM.Default_Certainty from defs_IF_Methods as IFM, defs_Input_Filters as IF where IFM.Input_Filter = IF.OBJECTID and IF.Code = ?"
    results = db_cursor.execute(select_string,str(default_input_filter))
    
    for row in results:
        return set_id,row.Default_Certainty,row.Default_Observation_Type,row.OBJECTID
    
def new_records(zones): # to be used for adding entirely new records to the database

    set_id,certainty,presence_type,if_method = get_defaults()
    
    import datetime
    l_date = datetime.datetime.now()
    l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
        
    insert_string = "insert into Observations (Set_ID,Species_ID,Zone_ID,Presence_Type,IF_Method,Certainty,Observation_Date, Notes) values (?,?,?,?,?,?,?,?)" 

    for zone in zones:
        db_cursor.execute(insert_string,set_id,species,zone,presence_type,if_method,certainty,l_date_string,reason_message)

def modify_records(zones):
    
    for zone in zones:
        
        w_clause = "Species_ID = ? and Zone_ID = ?"
                
        if where_string:
            w_clause = "%s and %s" % (w_clause,where_string)
        
        invalidate_records(w_clause,species,zone)
        
        if operation == "Remove": # if we're not moving it, then delete the records
            delete_string = "delete from Observations where %s" % w_clause
            db_cursor.execute(delete_string,species,zone)
        elif operation == "Transfer": # we have a fish to move to
            update_string = "update Observations set Species_ID = ? where %s" % w_clause
            db_cursor.execute(update_string,new_species,species,zone)
        else:
            arcpy.AddError("Specified operation: %s - however, the other parameters specified are insufficient to complete that operation" % operation)
            sys.exit()
            
def invalidate_records(w_clause,species,zone):
    # move the records over to Invalid_Observations
    
    if w_clause == "": # if it's empty:
        raise vars.DataStorageError("Can't invalidate records without a where clause - are you trying to nuke the whole database???")
    
    #log.write("Pyodbc version: %s", pyodbc.__version__)
    select_string = "select * from Observations where %s" % w_clause
    #log.write(select_string)
    #log.write(species)
    #log.write(zone)
    records = db_cursor.execute(select_string,species,zone)
    l_cursor = db_conn.cursor()
    
    insert_string = "insert into Invalid_Observations (OBJECTID,Set_ID,Species_ID,Zone_ID,Presence_Type,IF_Method,Certainty,Longitude,Latitude,Survey_Method,Notes,Observation_Date,Other_Data,Invalid_Notes) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    
    for record in records:
        l_cursor.execute(insert_string,record.OBJECTID,record.Set_ID,record.Species_ID,record.Zone_ID,record.Presence_Type,record.IF_Method,record.Certainty,record.Longitude,record.Latitude,record.Survey_Method,record.Notes,record.Observation_Date,record.Other_Data,reason_message)
    
    # close the subcursor
    l_cursor.close()

# open the database connection
log.write("Getting Zones")
zones = []
get_zones(layer,zones,"HUC_12") # fills the zones array with the zones to work with

if operation == "Add": # if we have a species, but not a current one, then we're adding new records
    new_records(zones)
else: # otherwise, we're modifying existing records
    modify_records(zones) # handles records whether they are being modified or deleted entirely

db_conn.commit()
log.write("Completed modifications, generating new layer!")

#if update_range == "True": # it's an == "True" because we get param as text
import mapping
queries = mapping.get_custom_queries(10,db_conn) # query set 10 is the one that defines the query to return a distribution
zones_layer = mapping.refresh_zones()
l_layer = mapping.map_layer(queries[0],species)

l_layer.populate(db_cursor)
l_layer.make(zones_layer,db_cursor)
l_layer_name = arcpy.CreateScratchName("mod_records","","FeatureClass",vars.workspace)
try:
    arcpy.CopyFeatures_management(zones_layer,l_layer_name)
except:
    log.error("failed to output temporary features")
    raise

params = arcpy.GetParameterInfo()
params[8].symbology = os.path.join(vars.internal_workspace,"mxds","base","gen_3.lyr")
arcpy.SetParameterAsText(8,l_layer_name)

# close the database connection
funcs.db_close(db_cursor, db_conn)

