import arcpy, os, sys
import vars, args, log
import funcs
from script_tool_funcs import *

'''This script is meant to be run only as an ArcGIS script tool - messages will be passed out using arcpy'''

print "This script should only be run as an ArcGIS script tool. If you can see this message, you should exit or you better know what you are doing"

#set up the workspace
vars.set_workspace_vars("C:/Users/nrsantos/Documents/PISCES")
log.initialize("opening for display_query.py",arc_script = 1)
#args.check_args()

# general
query = arcpy.GetParameterAsText(0)
species = arcpy.GetParameterAsText(1)
other_bind = arcpy.GetParameterAsText(2)

if species == None:
    log.error("No species to work on, exiting")
    sys.exit()

species = parse_input_species_from_list(species)
 
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
        
        # move the records over to Invalid_Observations
        select_string = "select * from Observations where Species_ID = ? and Zone_ID = ?"    
        records = db_cursor.execute(select_string,species,zone)
        l_cursor = db_conn.cursor()
        
        insert_string = "insert into Invalid_Observations (OBJECTID,Set_ID,Species_ID,Zone_ID,Presence_Type,IF_Method,Certainty,Longitude,Latitude,Survey_Method,Notes,Observation_Date,Other_Data,Invalid_Notes) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        
        for record in records:
            l_cursor.execute(insert_string,record.OBJECTID,record.Set_ID,record.Species_ID,zone,record.Presence_Type,record.IF_Method,record.Certainty,record.Longitude,record.Latitude,record.Survey_Method,record.Notes,record.Observation_Date,record.Other_Data,reason_message)
        
        # close the subcursor
        l_cursor.close()
        
        if operation == "Remove": # if we're not moving it, then delete the records
            delete_string = "delete from Observations where Species_ID = ? and Zone_ID = ?"
            db_cursor.execute(delete_string,species,zone)
        elif operation == "Transfer": # we have a fish to move to
            update_string = "update Observations set Species_ID = ? where Zone_ID = ? and Species_ID = ?"
            db_cursor.execute(update_string,new_species,zone,species)
        else:
            arcpy.AddError("Specified operation: %s - however, the other parameters specified are insufficient to complete that operation" % operation)
            sys.exit()

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
params[7].symbology = os.path.join(vars.internal_workspace,"mxds","base","gen_3.lyr")
arcpy.SetParameterAsText(7,l_layer_name)

# close the database connection
funcs.db_close(db_cursor, db_conn)

