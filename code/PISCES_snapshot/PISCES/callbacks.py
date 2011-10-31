import arcpy, os, re
import log, vars

class empty_object:
    def __init__(self):
        pass
    
def postprocess_zones(zones_layer, db_cursor, cb_args, parent_layer):
    '''
        Takes each record in the zones_layer and runs queries related to them.
        Queries should specify the place to include the zone with sql bind variables "?" and the variable operators specified by object location relative to parent_layer (eg: {custom_query.bind_var}) are optional
        Flexible:{object path from parent layer being worked on} - example {custom_query.bind_var} would return parent_layer.custom_query.bind_var and dump it into the query at that location
        Argument Format: query,column_name,column_data_type,query,column_name,column_data_type,query...etc
        Notes: the value to be placed in the column for a given query should be selected "AS col_value" - that's what the following code will be looking to retrieve
    '''
    
    arcpy.env.overwriteOutput = True
    
    log.write("Postprocessing zones - this may take some time!",1)
    #log.write("%s queries for layer" % len(cb_args) / 2)
    
    l_temp_file = os.path.join(vars.workspace,"postprocessing_temp")
    arcpy.CopyFeatures_management(zones_layer,l_temp_file) #copy any selected zones out

    # structure the queries out of the arguments    
    t_count = 0
    l_queries = []
    while t_count < len(cb_args):
        t_query = empty_object()
        t_query.query = cb_args[t_count]
        t_query.column = cb_args[t_count+1]
        t_query.col_type = cb_args[t_count+2]
        
        try:
            arcpy.AddField_management(l_temp_file,t_query.column,t_query.col_type) # add the column
        except:
            raise vars.MappingError("Unable to run callback postprocess_zones - error adding field %s" % t_query.column)
        
        # replace entities in the query
        while True: # find any object requests in the query - this is bad way to do this, but it "should" break on the first non_match
            m_object = re.search("({.+?})", t_query.query) # {.+?}
            
            if m_object == None:
                break
            match_item = m_object.group(0)
            
            #get the path to the object
            if "." in match_item: # if it has multiple parts, split it into a tuple
                object_parts = match_item.split(".")
            else: # otherwise, make our own one item tuple
                object_parts = match_item, # make it a single item tuple
            
            replace_object = parent_layer # start with the layer object
            for part in object_parts: # then for each portion of the object path
                try:
                    replace_object = replace_object.__dict__[part] # get that part and set it as the object to replace - effectively, move "down" the object
                except: # I see this being very possibly called - specifying a bad path would cause this (IndexError?)
                    raise vars.MappingError("Unable to run callback postprocess_zones - couldn't get custom entity specified in {%s}" % match_item)
                
            t_query.query.replace("{%s}" % match_item,replace_object)
        
        l_queries.append(t_query)
        
        t_count = t_count + 3 # skip the next 2 records
        
    rows = arcpy.UpdateCursor(l_temp_file)
    
    # for each row
    for row in rows:
        
        #check that it's a HUC
        if row.HUC_12 == None:
            print "skipping row..."
            continue
        
        # then run the queries
        for query in l_queries:

            db_cursor.execute(query.query,row.HUC_12)
            l_result = db_cursor.fetchone() # just get me the first row. There only should be one anyway... 
            row.setValue(query.column,l_result.col_value)            
        
        rows.updateRow(row) # save it!
    
    del row
    del rows # cleanup
    arcpy.env.overwriteOutput = False
    
    # read it back in
    zone_layer = "PostProcess_Zones"
    arcpy.MakeFeatureLayer_management(l_temp_file,zone_layer)

    # return it
    return zone_layer
    

def richness(zones_layer, db_cursor, cb_args, parent_layer): #layer callback
    # note - exceptions are already being caught by the caller
    
    arcpy.env.overwriteOutput = True
    
    log.write("Building species richness layer - this may take some time!",1)
    
    l_temp_file = os.path.join(vars.workspace,"richness")
    arcpy.CopyFeatures_management(zones_layer,l_temp_file) #copy any selected zones out
        
    arcpy.AddField_management(l_temp_file,"Richness","LONG") # add the column
    
    rows = arcpy.UpdateCursor(l_temp_file)
    
    if not (cb_args == None or cb_args is False):
        sql_ext = cb_args
    else:
        sql_ext = ""

    log.write("sql extension on callback: %s" % sql_ext,1)
    
    for row in rows:
        if row.HUC_12 == None:
            print "skipping row..."
            continue

        l_sql = "SELECT Count(*) AS l_count FROM (select distinct Observations.Species_ID from Observations, Species where Observations.Zone_Id = ? and Observations.Species_ID = Species.FID " + sql_ext + ")"
        db_cursor.execute(l_sql,row.HUC_12)
        
        l_result = db_cursor.fetchone() # just get me the first row. There only should be one anyway... 
        row.Richness = l_result.l_count # the first row of the result and the first item in that row
        
        rows.updateRow(row) # save it!
    
    del row
    del rows # cleanup
    arcpy.env.overwriteOutput = False
    
    # read it back in
    zone_layer = "Richness_Zones"
    arcpy.MakeFeatureLayer_management(l_temp_file,zone_layer)

    # return it
    return zone_layer


def genus_family_richness(zones_layer,db_cursor,gf, parent_layer): #layer callback
    # note - exceptions are already being caught by the caller
    
    arcpy.env.overwriteOutput = True
    
    log.write("Building family richness layer - this may take some time!",1)
    
    l_temp_file = os.path.join(vars.workspace,"richness")
    arcpy.CopyFeatures_management(zones_layer,l_temp_file) #copy any selected zones out
        
    arcpy.AddField_management(l_temp_file,"Richness","LONG") # add the column
    
    rows = arcpy.UpdateCursor(l_temp_file)
    
    for row in rows:
        l_sql = "SELECT Count(*) AS l_count FROM (select distinct Family from species where FID = (select distinct Species_ID from Observations where Zone_Id = ?))"
        db_cursor.execute(l_sql,row.HUC_12)
        
        l_result = db_cursor.fetchone() # just get me the first row. There only should be one anyway... 
        row.Richness = l_result.l_count # the first row of the result and the first item in that row
        
        rows.updateRow(row) # save it!
    
    del row
    del rows # cleanup
    arcpy.env.overwriteOutput = False
    
    # read it back in
    zone_layer = "Richness_Zones"
    arcpy.MakeFeatureLayer_management(l_temp_file,zone_layer)

    # return it
    return zone_layer

def make_tooltip_column(zones_layer,db_cursor,args):
    
    arcpy.env.overwriteOutput = True
    
    log.write("Building tooltip",1)
    
    l_temp_file = os.path.join(vars.workspace,"tooltip")
    arcpy.CopyFeatures_management(zones_layer,l_temp_file) #copy any selected zones out
        
    arcpy.AddField_management(l_temp_file,"Tooltip","LONG") # add the column
    
    rows = arcpy.UpdateCursor(l_temp_file)
    
    for row in rows:
        if row.HUC_12 == None:
            print "skipping row..."
            continue

        l_sql = "SELECT DISTINCT Observation_Sets.* FROM Observation_Sets, Observations WHERE Observations.Species_ID = ? and Observations.Zone_ID = ? and Observations.Set_ID = Observation_Sets.Set_ID;"
        db_cursor.execute(l_sql,row.HUC_12) # TODO: Needs to use a query brought in by argument and needs a way to bring in the species and pass it as a bind variable - need a robust system for operators in the text that get replaced before the bind arguments are passed in.
        
        l_result = db_cursor.fetchone() # just get me the first row. There only should be one anyway... 
        row.Richness = l_result.l_count # the first row of the result and the first item in that row
        
        rows.updateRow(row) # save it!
    
    del row
    del rows # cleanup
    arcpy.env.overwriteOutput = False
    
    # read it back in
    zone_layer = "Richness_Zones"
    arcpy.MakeFeatureLayer_management(l_temp_file,zone_layer)

    # return it
    return zone_layer

def clipped_layer_overlay(zones, clip_layer=None):
    
    log.write("Running callback clipped_layer_overlay for feature %s" % clip_layer)
    if clip_layer is None: # default to all_rivers
        clip_layer = os.path.join(vars.geo_aux,all_rivers)
    
    unique_arc_name = arcpy.CreateUniqueName("temp_",vars.workspace) # generate a unique name for the zones dissolve 
    arcpy.Dissolve_management(zones,unique_arc_name) # dissolve the HUCs so that the input is
    
    unique_arc_name_2 = arcpy.CreateUniqueName("temp_mapping_result_",vars.workspace) 
    arcpy.Clip_analysis(clip_layer, zones, unique_arc_name_2) # clip the input to the dissolved zones and put it in unique_arc_name_2
     
    # return clip_layer
    return unique_are_name_2

    



def forest_listing(zones_layer,db_cursor,args): # map callback
    pass    