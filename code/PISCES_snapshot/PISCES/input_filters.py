import arcpy, os
import vars, log, funcs, string, observations
import re

#List of possible filters that gets checked
IF_List = {} # this will be filled in on program init
if_methods = {} # dictionary containing all IF Methods. Indexed by Filter_Code, each dictionary value is an array of if_method objects that can be looked up by code
field_maps = {} # indexed by set id number, but not necessarily contiguous. Each entry is an array of the items required for a set
alt_codes_by_filter = {} # each dictionary entry (input filter is the key) holds another dictionary where the alt_code returns the species id
database_mapping = {'Species':"species_fid",'Date': "obs_date", 'Latitude':"lat",'Longitude':"long",'Observation Type':"obs_type",'Observer':"observer",'Survey Method':"survey_method",'Certainty':"certainty"} # ok, now this is ridiculous...field maps inside of field maps. Am I in the twilight zone? This variable - using this makes some code relatively ugly, but it's necessary to make things human readable - maybe this original mapping needs to live in the database in some way... 

class input_filter: #parent class to all actual input filters that describe
    
    def __init__(self,full_obs_set):
        # full_obs_set is the object that this input filter is a part of. It's so we can access the data in that class
        # we should probably think about whether or not there is a better way to achieve that goal.
        self.all_init(full_obs_set)
  
    def all_init(self,full_obs_set): # called by __init__ of input filters in order to have a constant set of things that gets called before anything happens
        self.parent = full_obs_set
        # this way self.parent gets us the object that this filter is contained in (NOT the parent class)
        
        self.name_match_string = None
        self.name_match_group = None
        
        self.if_methods = None
        self.default_observer = None
        
        self.set_up_field_maps()
        
        self.get_defaults()
        
    def set_up_field_maps(self):
        
        global field_maps
        
        self.fmap_index = {} # set it up - we want to have a lookup for "lat", etc that returns the entry, from which we can grab the column or other data
        self.field_map = []
        
        if field_maps.has_key(self.parent.new_data.ID):       
            for l_map in field_maps[0]: # copy the defaults out - we can't just assign the larger array over because we're going to swap out items and we don't want that to happen to all of them 
                self.field_map.append(l_map)
        
            for index in range(len(field_maps[self.parent.new_data.ID])): # overwrite the defaults with the more specific copy, if available - iterate over the loops and copy out the specific one in place of the default when their names match
                for d_index in range(len(self.field_map)):
                    if field_maps[self.parent.new_data.ID][index].field_name == self.field_map[d_index].field_name:
                        self.field_map[d_index] = field_maps[self.parent.new_data.ID][index]
            
            self.index_field_maps() # throw the data in
               
        
    def get_defaults(self):
        # this is incredibly inefficient to do this for every input filter, but a more robust method that caches it doesn't yet make sense. If we start to get more variables, maybe a cache is wise

        db_cursor,db_conn = funcs.db_connect(vars.maindb, "Getting defaults for input filter")
        
        code = self.parent.filter_code
        
        sql = "select Default_Observer from defs_Input_Filters where Code = ?"
        rows = db_cursor.execute(sql,code)
        
        for row in rows: # there should only be one - if there is more, then this takes the last one
            self.default_observer = row.Default_Observer
        
        funcs.db_close(db_cursor, db_conn)
    
    def determine_species(self, match_string):
        log.write ("parsing dataset name for species determination in dataset %s" % self.parent.dataset_name)
        
        if not self.name_match_string == None:
            l_match = re.search(self.name_match_string,match_string) # pull out the data we need from the filename
        
            l_alt_code_species = l_match.group(self.name_match_group) #pops the match from the previous search into there. Now we need to check if it's a species code or if its an alt_code
            # name match group is previously defined in case we want to match multiple spots
        else:
            l_alt_code_species = match_string
        
        if vars.all_fish.has_key(l_alt_code_species): # Validate: if it has the key for the id, then we have a fish
            self.parent.species_fid = l_alt_code_species # we can expand this as we expect more data in the filename
            log.write(auto_print = 1, log_string = "Fish species identified for feature class %s. Species %s" % (self.parent.dataset_name,l_alt_code_species))
        else:
            l_species = funcs.get_species_from_alt_code(l_alt_code_species,self.parent.filter_code)
            if l_species is False: # if the function couldn't find it, raise the error which will stop processing this set since it's the last attempt we can make
                raise vars.DataProcessingError("Unable to determine species for %s (using alt_code %s) - it's probably going to be easiest for you to just define it yourself in the New_Data.mdb record (replace 'filter' in the record with something valid as explained on the input form)" % (self.parent.dataset_name,l_alt_code_species),self.parent.dataset_key)
            else: # if it found one, set it and return
                self.parent.species_fid = l_species
    
    def process_observations(self):
        return
    
    def make_results(self,zones,species,obs_type,pri_cert,sec_cert = None,if_method = None):
        
        l_result = vars.result_set() #make the result to store the data in
        
        l_observations = [] # make the observations array
        for zone in zones:
            l_obs = vars.observation() # make the observation for this index
            l_obs.zone = zone
            l_obs.species_fid = species
            l_obs.obs_type = obs_type
            l_obs.certainty = determine_certainty((pri_cert,sec_cert)) # primary, secondary
            l_observations.append(l_obs)
        l_result.observations = l_observations
        l_result.if_method = if_method
        #l_result.temporary_dataset = out_feat
        
        return l_result   
    
    def index_field_maps(self):
        for l_map in self.field_map:
            self.fmap_index[l_map.field_name] = l_map            
    
class if_method:
    
    def __init__(self):
        self.method_id = None #corresponds with OBJECTID 
        self.short_name = None
        self.description = None
        self.default_observation_type = None
        self.default_certainty = None 
        self.trigger = None # the thing to use when we're iterating 

class field_map:
    
    def __init__(self):
        self.set_id = None # needs this since before being assigned to the input data, this will sit in a list/dict
        self.field_name = None
        self.matched_field = None # this might not be needed - this is in case the actual field varies from the name specified in field name - this would be the database table.column we actually want to use
        self.input_field = None
        self.handler_function = None # this is just the name we pull from the db
        self.handler_function_object = None # this is the retrieved object to run

class empty_row:
    
    def __init__(self):
        pass
    
    def fields_to_notes_string(self, fields): # fields comes in as a tuple of field names
        
        l_string = ""
        
        for item in fields:
            if self.__dict__.has_key(item): # if it actually exists - otherwise we'll get a key error
                l_string = "%s%s: %s; \n" % (l_string,item,self.__dict__[item]) 
            
        return l_string
    
    # this class is just a base to attach unknown attributes to in the multifeature_to_HUCs function

class empty_field:
    def __init__(self):
        self.value = None
        self.fielddata = None

class Gen_Poly_IF(input_filter):
    
    def __init__(self,full_obs_set):
        self.all_init(full_obs_set) # sets all the defaults for us
        
    def determine_species(self):
        print self.name_match_string
        input_filter.determine_species(self,self.parent.dataset_name)
            
    def process_observations(self):
        # TODO: Comment this function
        # TODO: much of this function can probably be abstracted once we get more IF methods
        #Run the analysis
        
        print "Processing dataset %s" % self.parent.dataset_path
        
        for method in if_methods[self.parent.filter_code]:
            
            if not self.parent.new_data.IF_Method == None: # if we were told to only use a particular IF Method
                if not self.parent.new_data.IF_Method == method.short_name: # and we aren't using it!
                    continue # then skip this round
            
            results = multifeature_to_HUCs(self.parent.dataset_path,method.trigger)
            HUCS = []
            for row in results:
                HUCS.append(row.HUC_12) #bundle the HUCs - this lets us become compatible with the code below for now
            
            obs_type = self.parent.new_data.Presence_Type
            if obs_type == None:
                obs_type = method.default_observation_type
             
            l_result = self.make_results(HUCS,self.parent.species_fid,obs_type,method.default_certainty,observations.observation_certainties[str(method.default_observation_type)],method)
                            # zones, observation_type, certainty 1, fallback certainty, if method id
            
            self.parent.results.append(l_result)
        
        #TODO: Write line to the data log indicating changes
 
class Gen_Table_IF(input_filter):
    '''Generic Filter for tables that have a species column and a column for x/y - we can base future classes on this
     subclasses can extend the functionality of this class by polymorphosing (defining a new) the method process_observations,
     and then calling parent class's version of .process_observations() after all the prep work is done. This would be a good way
     to do things like splitting data columns and any other *very* item specific processing (generic processing would ideally)
     be incorporated into this class '''

    def __init__(self,full_obs_set):
        self.all_init(full_obs_set) # sets all the defaults for us - defined in the main input_filter class        
        self.handle_args()
        self.survey_method = self.parent.new_data.Survey_Method
        
    def handle_args(self):
        self.args = self.parent.new_data.Input_Filter_Args
        #args_array = string.split(self.args,";")
        
            
    def determine_species(self): #override default for determining the species
        #must set self.parent.species_fid
        if self.parent.new_data.Species_ID == None or self.parent.new_data.Species_ID == "filter":
            self.parent.species_fid = "MUL99"
        else:
            input_filter.determine_species(self,self.parent.new_data.Species_ID) # call the parent class' generic version - in some cases, more handling can be done here, but in most cases, the parent class will handle the full range of possibilities
        
    def determine_species_for_record(self, species):
    
        if species == None:
            return False
        
        species = string.upper(str(species))
        if vars.all_fish.has_key(species):
            return self.vars.all_fish[species]
        else:
            l_species = funcs.get_species_from_alt_code(species,self.parent.filter_code)
            if not l_species is False: 
                return l_species
            
        return False # if we've gotten to here, then we don't know what species it is. False will skip the record
        
    def process_observations(self):
        
        log.write("Processing %s" % self.parent.dataset_name,1)
        
        method = if_methods[self.parent.filter_code][0] # currently uncertain of a way to make this handle multiple if_methods. It might be unnecessary though, so we'll cross that bridge when we get there
        self.parent.obs_type = method.default_observation_type
        
        ### Figure out what it is so we can process it either as a table or as a multispecies feature class
        try:
            describer = arcpy.Describe(self.parent.dataset_path)
        except:
            raise vars.DataProcessingError("Unable to determine object type")
        if describer.dataType == "Table":
            try:
                l_features = tablecoords_to_file(self.parent.dataset_path,self.fmap_index,self.parent.new_data.Projection_Key) # dataset, field name for x axis, field name for y axis, and the projection they are all in
            except vars.DataProcessingError as lerror:
                print lerror
                return # skip this dataset!
        else:
            l_features = self.parent.dataset_path
        
        HUCs = multifeature_to_HUCs(l_features) # TODO: FIX
        
        if describer.dataType == "Table": # we only want to delete the feature class if the initial file was a table because that means we created it here - otherwise we want to save it still
            arcpy.Delete_management(l_features) # we're through with it - delete it because the same name will be used should tablecoords_to_file be called again
        
        del describer # a bit of memory management
        
        l_result = vars.result_set() # make the result set
        l_observations = [] # the observations array that will be plugged into the result set
        
        for row in HUCs:

            observation = vars.observation() # make the observation
            
            if self.fmap_index.has_key("Species"): # it legitimately might not - it's possible this table is entirely for one species
                observation.species_fid = self.determine_species_for_record(row.__dict__[self.fmap_index["Species"].input_field]) # get the species for this record
                if observation.species_fid is False: # if it's for a species that we either aren't tracking or couldn't be determined, then
                    continue    # skip this record. A continue here prevents this whole loop iteration's data from being appended.
            elif (not self.parent.species_fid == None) and (not self.parent.species_fid == "MUL99"):
                    observation.species_fid = self.parent.species_fid
            else: # we don't have a field, and we don't have a species id for the dataset
                continue # skip it!
            
            # TODO: this should be coded as a var somewhere so we can do row.__dict__[zones_field]
            observation.zone = row.HUC_12

            # set the big, important values that we have a field map for            
            global database_mapping
            
            continue_flag = 0
            
            notes_fields = str(self.fmap_index["NotesItems"].input_field).split(';') # figure out which fields are part of the notes
            observation.other_data = row.fields_to_notes_string(notes_fields) # process it first so we can chuck it from the field map
            
            for item in self.field_map:
                if item is self.fmap_index["NotesItems"] or item is self.fmap_index["Species"]: # we already processed this - skip it - theoretically species could be integrated, but it'd be a pain for end users
                    continue                
                
                l_function = self.get_handler(item)
                if l_function is True: # if we have a function, pass the column value through it first. If we have a function, but not a column, the function should return a default
                    try:
                        l_value = item.handler_function_object(item,observation,row,method) # pass it a bunch of extra information by default so that it should be able to do anything it needs
                    except vars.DataProcessingError as lerror: # if we get an error raised, set the flag so that we can skip this record - we can't reliably work with this record anymore
                        print lerror
                        continue_flag = 1
                elif l_function is False and not (row.__dict__[item.input_field] == None): # we don't have a function, but we do have a field
                    l_value = row.__dict__[item.input_field]
                else: # we have neither function nor field
                    l_value = None
                    
                observation.__dict__[database_mapping[item.field_name]] = l_value # observations field  
            
            if continue_flag == 1:
                continue # something went wrong - continue before we append

            #observation.notes = "(x,y) in 1983 UTM Z10N"
                        
            l_observations.append(observation)
            
        l_result.observations = l_observations # add all of this to the results object
        l_result.if_method = method
        
        #l_result = self.make_results(HUCs,method.default_observation_type,method.default_certainty,method.default_observation_type,method.method_id)
                                    # zones, observation_type, certainty 1, fallback certainty, if method id
                                    
        self.parent.results.append(l_result)
        
    def get_handler(self, l_map):
        if not l_map.handler_function == None:
            try:
                l_map.handler_function_object = getattr(self, l_map.handler_function) # this is PROBABLY wrong - the functions will likely be stored differently as part of an object...
                return True # yes, an object
            except AttributeError: # there is SUPPOSED to be a function, but we can't find it! ERROR
                raise vars.DataProcessingError("Unable to create handler function for field map for set %s and field %s" % (l_map.set_id,l_map.field_name))
        else:
            return False # no object
       
       
    ####
    ##   Default Handlers!
    ####
    def handle_certainty(self,item,observation,row,method):
        '''meant to be overridden by subclasses - as it is, it just returns the default. This way, though, subclasses can override these small parts without having to override
           the entire process_observations() behemoth.'''
           
        return method.default_certainty
    
    def handle_species(self,item,observation,row,method): # TODO: this function should not actually get used - it's a relic - consider removal!
        if row.__dict__.has_key(item.input_field):
            return row.__dict__[item.input_field]
        else: # we should NEVER be here - if we've gotten this far without a valid species field...
            raise vars.DataProcessingError("Could not find a species for record - skipping")
    
    def handle_latitude(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field):
            return row.__dict__[item.input_field]
        elif item.required is True: # we should NEVER be here - if we've gotten this far without a valid lat field... - this could be popping up unexpectedly for you if you didn't define a lat field - in this case, it uses the default field map which includes one
            raise vars.DataProcessingError("Could not find a latitude for record - skipping")
        else:
            return None
    
    def handle_longitude(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field):
            return row.__dict__[item.input_field]
        elif item.required is True: # we should NEVER be here - if we've gotten this far without a valid long field... - this could be popping up unexpectedly for you if you didn't define a long field - in this case, it uses the default field map which includes one
            raise vars.DataProcessingError("Could not find a longitude for record - skipping")
        else:
            return None
    
    def handle_date(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field): # if we have a field, return its value for the row
            return row.__dict__[item.input_field]
        elif item.required is True: # if we don't, and it's required, raise the error - it will be caught and the record skipped
            raise vars.DataProcessingError("Could not find a date for record - skipping")
        else: # if there isn't a field, and it's not required, we don't care
            return None
        
    def handle_observer(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field): # if we have a field, return its value for the row
            return row.__dict__[item.input_field]
        else:
            if not self.parent.observer == None: # for this default function, return the parent dataset's info if it exists
                return self.parent.observer
            elif not self.default_observer == None:
                return self.default_observer
            elif item.required is True: # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
                raise vars.DataProcessingError("Could not find an observer for record - skipping")
            else: # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
                return None
    
    def handle_obs_type(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field): # if we have a field, return its value for the row
            return row.__dict__[item.input_field]
        else:
            if not method.default_observation_type == None: # for this default function, return the parent dataset's info if it exists
                return method.default_observation_type
            elif item.required is True: # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
                raise vars.DataProcessingError("Could not find an observation type for record - skipping")
            else: # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
                return None
    
    def handle_survey_method(self,item,observation,row,method):
        if row.__dict__.has_key(item.input_field): # if we have a field, return its value for the row
            return row.__dict__[item.input_field]
        else:
            if not self.parent.survey_method == None: # for this default function, return the parent dataset's info if it exists
                return self.parent.survey_method
            elif item.required is True: # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
                raise vars.DataProcessingError("Could not find a survey method for record - skipping")
            else: # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
                return None
            
class CNDDB_IF(Gen_Table_IF):
    
    def handle_obs_type(self,item,observation,row,method):
        if row.OCCTYPE == "Introduced Back into Native Hab./Range" or row.OCCTYPE == "Natural/Native occurrence":
            if row.PRESENCE == "Possibly Extirpated" or row.PRESENCE == "Extirpated":
                return 3 # historical distribution
            else: # other option for CNDDB is "Presumed Extant"
                return 1 # extant
        if row.OCCTYPE == "Refugium; Artificial Habitat/Occurrence" or row.OCCTYPE == "Transplant Outside of Native Hab./Range":
            if row.PRESENCE == "Possibly Extirpated" or row.PRESENCE == "Extirpated":
                raise vars.DataProcessingError("Untrackable CNDDB observation - skipping - occurence type suggests extirpated nonnative species") # If it's nonnative and extirpated, we don't quite care here - we don't track that - raise DataProcessingError in order to have it culled ("None resulted in it being inserted anyway, with no obs_type, which is fine for most queries, but bad for ones that don't track that)
            else: # other option for CNDDB is "Presumed Extant"
                return 6 # translocated
        else:
            raise vars.DataProcessingError("Invalid CNDDB record - no occurrence type (OCCTYPE) specified that we understand - we understand 'Introduced Back into Native Hab./Range', 'Natural/Native occurrence', 'Refugium; Artificial Habitat/Occurrence', and 'Transplant Outside of Native Hab./Range' - this row has '%s'" % row.OCCTYPE)
    
    
def tablecoords_to_file(dataset_path,field_map,projection_index):
    # args: dataset to work on, the field that contains the x coord, the field containing the y coord, and the projection file to use
    
    print "Converting Coordinates to Feature Class"
    
    if projection_index == None:
        raise vars.DataProcessingError("No projection specified for dataset %s" % dataset_path)

    l_rows = table_to_array(dataset_path,True)

    index = 0
    l_max = len(l_rows)
    while index < l_max: # we're going to check to make sure that we have x,y for each
        try:
            if l_rows[index].__dict__[field_map["Longitude"].input_field].value == None or l_rows[index].__dict__[field_map["Latitude"].input_field].value == None: # if we don't have a value for both
                del l_rows[index]
                l_max = len(l_rows) #update the iteration count
            else:
                index = index + 1 # only increment when we aren't deleting and items since everything following will move forward by one when we do 
        except:
            raise vars.DataProcessingError("Unable to retrieve coordinates from %s - check your field map" % dataset_path)
    return reproject_coords(l_rows,field_map["Longitude"].input_field,field_map["Latitude"].input_field,vars.projections[projection_index])

def table_to_array(dataset_path,transfer_object = False): # takes a path to an arcgis table (or any shape with a table) and returns an array of objects with the fields as attributes and the data filled in.
    
    '''somewhere along the path of creating the set of functions that this function supports, we went the roundabout way. It is likely possible that simply creating a point
        at the x,y specified in the column and assigning the .shape attribute the the point would work. Even if that didn't work, it's still very possible that a more direct conversion
        of the table to a shape would work. For now, this code functions well and is pretty robust so I'm not willing to remove this code, but note that a potentially
        serious speedup may be possible through a less roundabout method (we arrived here as requirements changed while coding)'''
    
    l_fields = arcpy.ListFields(dataset_path)
    for index in range(len(l_fields)):
        if(l_fields[index].type == "OID"): #for whatever reason, Arc Has issues here... make sure we don't run into issues with the OBJECTID column - don't copy it
            del l_fields[index]
            break
    
    l_cursor = arcpy.SearchCursor(dataset_path)
    
    l_rows = []

    if transfer_object == True:
        ''' stepping through this: This if statement really only relates to the nested for loop, but is out here to save some speed
            In the case that transfer_object is true, then we copy the whole field object over to fielddata and then the value into .value - this way we can access the field structure every time that field is used while the value remains discrete
            In the else case, it just stores the value for something where we aren't looking to recreate the table - just access it
        '''      
        for row in l_cursor: # for each row in the result
            l_row = empty_row()
            for field in l_fields: # and for every field in that row                    
                l_row.__dict__[field.name] = empty_field()
                l_row.__dict__[field.name].fielddata = field
#                if l_row.__dict__[field.name].fielddata.type == "OID":
#                    l_row.__dict__[field.name].fielddata.type = "Integer"
#                    l_row.__dict__[field.name].fielddata.name = "Old_ID"
                l_row.__dict__[field.name].value = row.getValue(field.name)
            l_rows.append(l_row)
    else:
        for row in l_cursor: # for each row in the result
            l_row = empty_row()
            for field in l_fields: # and for every field in that row
                l_row.__dict__[field.name] = row.getValue(field.name) # create an attribute in the __dict__ for this instance of empty_row and set its value to the value in the table
            l_rows.append(l_row)
        
    return l_rows

def get_IF_list():
    
    log.write("Getting input filter information from the database")
    
    l_sql = 'SELECT Code, Class FROM defs_Input_Filters;'
    l_cursor,l_conn = funcs.db_connect(vars.maindb)
    
    l_data = l_cursor.execute(l_sql)
    
    for filter in l_data:
        IF_List[filter.Code] = filter.Class
    
    funcs.db_close(l_cursor,l_conn)
    
    return

def retrieve_if_methods():
    
    db_cursor, db_conn = funcs.db_connect(vars.maindb, "Retrieving IF_Methods")
    
    l_sql = """select
     defs_IF_Methods.OBJECTID, defs_IF_Methods.Short_Name, 
     defs_IF_Methods.Description, defs_IF_Methods.Default_Observation_Type, 
     defs_IF_Methods.Default_Certainty, defs_Input_Filters.Code,
     defs_IF_Methods.Trigger
     from defs_IF_Methods inner join defs_Input_Filters 
     on ((defs_IF_Methods.Input_Filter) = defs_Input_Filters.OBJECTID)
     """
     
    db_results = db_cursor.execute(l_sql) # get all of the IF_Methods for this input filter type
    
    for result in db_results: #map them to a if_method object and append it to the methods for this IF
        l_method = if_method()
        l_method.method_id = result.OBJECTID
        l_method.short_name = result.Short_Name
        l_method.description = result.Description
        l_method.default_observation_type = result.Default_Observation_Type
        l_method.default_certainty = result.Default_Certainty
        l_method.trigger = result.Trigger
        
        if not if_methods.has_key(result.Code):
            if_methods[result.Code] = []
        
        if_methods[result.Code].append(l_method)
        
    funcs.db_close(db_cursor, db_conn)
    

def multifeature_to_HUCs(feature = None,relationship = "INTERSECT"): 
    '''base function that when provided with a feature class with multiple features
     in it and a column containing the species designation will return a multipart feature for each species'''
     
    ''' usage: multifeature_to_HUCS(feature_class_location)
        returns: an array of objects, sorted by species with a .zone attribute and attributes for every field in the data table.'''
    
    print "Getting Zones for multiple features"
    
    if feature is None:
        log.write("multifeature_to_HUCs error: No feature provided - skipping", 1)
        return []
    
    arcpy.env.workspace = vars.workspace #make sure the workspace is set
    
    try:
        feature_layer = "feature_layer"
        arcpy.MakeFeatureLayer_management(feature,feature_layer)
    except:
        raise vars.DataProcessingError("Unable to make feature layer for %s" % feature)
    
    try:
        zones_layer = "zones_feature_layer"
        arcpy.MakeFeatureLayer_management(vars.HUCS,zones_layer)
    except:
        raise vars.DataProcessingError("Unable to make feature layer for zones")
    
    join_shape = os.path.join(arcpy.env.workspace,"temp_sjoin") #@UndefinedVariable
    
    arcpy.SpatialJoin_analysis(zones_layer,feature_layer,join_shape, "JOIN_ONE_TO_MANY", "KEEP_COMMON", match_option = relationship)
        # the above statement intersects the input features, transfers all of their attributes, discards zones without that aren't joined, and creates multiple copies of any zone where multiple input features (observations) occur
        # options for relationship defined by spatial join docs are INTERSECT,CONTAINS,WITHIN,CLOSEST - this defaults to INTERSECT but is taken as a function arg
    
    l_fields = arcpy.ListFields(join_shape)
    l_cursor = arcpy.SearchCursor(join_shape)
    
    zones = []

    for row in l_cursor: # for each row in the result
        l_row = empty_row()
        for field in l_fields: # and for every field in that row
            l_row.__dict__[field.name] = row.getValue(field.name) # create an attribute in the __dict__ for this instance of empty_row and set its value to the value in the table
        zones.append(l_row)  
        
    ### CLEANUP
    arcpy.Delete_management(feature_layer)
    arcpy.Delete_management(zones_layer)
    arcpy.Delete_management(join_shape)
    
    print "Completed Getting Zones - returning\n"
    return zones


def feature_to_HUCs(feature = None, intersect_centroid = "INTERSECT"):
    """intersect_centroid is just whether we want to overlap by intersect or centroid methods"""
    
    # TODO: Check the projection of the data. If vars.auto_project == 1, then reproject it using vars.proj_teale_albers, otherwise, throw an EXCEPTION
    
    ### Sample Usage
    #HUCs = []
    #HUCs,feature = input_filters.feature_to_HUCs(feature=os.path.join(vars.newdb,"MOY","hhpolychp"),"INTERSECT")
        
    ####
    #### Check data validity
    ####
    if feature is None:
        log.write("feature_to_HUCS error: No feature provided - skipping", auto_print=1)
        return []
    
    ####
    #### Set up variables
    ####
    HUC12_IDs = [] # define an empty array of the IDs
    arcpy.env.workspace = vars.workspace #make sure the workspace is set
    
    feature_name_parts = os.path.split(feature)
    feature_name = feature_name_parts[1] # get the part of the feature's path that's just the name
    
    selection_name = "HUC_Select_" + feature_name + "_" + intersect_centroid 
    # this name might be a bit long, but should identify info in a good way
    
    ####
    #### Make sure we aren't overwriting existing data
    ####
    try:
        funcs.remove_data(selection_name, vars.workspace)
    except:
        log.write("Unable to delete existing intersection data - cannot proceed",1)
        raise

    ####
    #### Select the features!
    ####
    try:
        feature_layer = "feature_layer"#_" + feature_name + "_" + intersect_centroid
        HUCs_layer = "all_HUCs"
        
        log.write("Making feature layers from feature classes for intersect - using %s" % feature)
        arcpy.MakeFeatureLayer_management(feature, feature_layer)
        arcpy.MakeFeatureLayer_management(vars.HUCS,HUCs_layer)
       
        log.write("Intersecting feature layer %s with HUCs via %s method" % (feature,intersect_centroid), 1)
        arcpy.SelectLayerByLocation_management(HUCs_layer, intersect_centroid, feature_layer, selection_type="NEW_SELECTION")
    except:
        log.write("Unable to intersect layer %s with HUCs via %s method" % (feature,intersect_centroid))
        raise
    
        
    ####
    #### Write the selected features to a new feature class
    ####
    arcpy.CopyFeatures_management(HUCs_layer, selection_name)
    
    ####
    #### Get the HUCs to store in the database
    ####
    rows = arcpy.SearchCursor(selection_name) 
    for row in rows:
        HUC12_IDs.append(row.getValue("HUC_12"))
    
    ###
    ### Delete the data layers so we can make new ones
    ###
    arcpy.Delete_management(feature_layer)
    arcpy.Delete_management(selection_name)
    arcpy.Delete_management(HUCs_layer) # deleting this and recreating it is probably inefficient if we do a lot of it. We could create it outside of the loop and pass it in, but the code is cleaner if we keep it all grouped as it is now
    
    ####
    #### Return the data
    ####
    return HUC12_IDs # selection_name is returned too so that the data can be dissolved and stored if necessary

def reproject_coords(rows,xaxis,yaxis,projection_file = vars.proj_utm):
    
    print "Projecting coordinates"
    
    arcpy.env.workspace = vars.workspace #confirm that the arcpy workspace is currently correct!
    point_fc_short = "project_point"
    point_fc = os.path.join(arcpy.env.workspace, point_fc_short) #@UndefinedVariable

    
    if not arcpy.Exists(point_fc):
        arcpy.CreateFeatureclass_management(arcpy.env.workspace,point_fc_short,"Point",'',"DISABLED","DISABLED",projection_file) #@UndefinedVariable
    else:
        log.write("temporary feature class already exists - deleting",1)
        arcpy.Delete_management(point_fc) # delete it and recreate it - to ensure it's clear
        arcpy.CreateFeatureclass_management(arcpy.env.workspace,point_fc_short,"Point",'',"DISABLED","DISABLED",projection_file) #@UndefinedVariable
    
    for item in rows[0].__dict__.keys(): # for every field that we have here
        arcpy.AddField_management(point_fc,rows[0].__dict__[item].fielddata.name,rows[0].__dict__[item].fielddata.type) # add it to the shape
    
    # add the points
    cur = arcpy.InsertCursor(point_fc)
    
    for index in range(len(rows)):
        new_feature = cur.newRow() # make a new row
        l_point = arcpy.Point(rows[index].__dict__[xaxis].value,rows[index].__dict__[yaxis].value) # make the point
        new_feature.shape = l_point # set the new row's geometry to the point
        for item in rows[index].__dict__.keys(): # set the values of its fields
            new_feature.setValue(item,rows[index].__dict__[item].value)
        cur.insertRow(new_feature) # complete the insert
    
    del cur
    
    # project that file
    result = os.path.join(arcpy.env.workspace,"project_point_proj") #@UndefinedVariable
    try:
        arcpy.Project_management(point_fc,result,vars.default_proj) # TODO: This should be a function that can be called by others. Theoretically other shapes should be projected!
    except:
        raise
        log.write("Unable to project the new points made from x/y data",1)
        arcpy.Delete_management(point_fc) # clean up
        raise vars.DataProcessingError
    
    arcpy.Delete_management(point_fc) # we're done with it now - just need the result
    
    return result
    

def find_HUC_by_latlong(lat,long): # THIS FUNCTION IS PROBABLY DEPRECATED. CHECK tablecoords_to_file -> multifeature_to_HUC workflow
    
    #TODO: modify this - it should take a tuple of lat longs and an optional projection file . It will then create the points, project them to teal albers if need be and intersect them. It then returns the HUCs intersected. This way, we save on operations creating feature classes, spatial joining, etc.
    
    """provided a lat/long pair (in Teale Albers meters!), it returns the HUC"""
    
    '''arcpy.env.workspace = vars.workspace #confirm that the arcpy workspace is currently correct!
    
    # TODO: this function should perform a sanity check. If the numbers are less than 1000, we were probably handed degrees
    
    log.write("finding HUC at %s, %s" % (lat,long),1)
    temp_fc = os.path.join(arcpy.env.workspace, "temp_point") #@UndefinedVariable

    if not arcpy.Exists(temp_fc):
        arcpy.CreateFeatureclass_management(arcpy.env.workspace,"temp_point","Point",'',"DISABLED","DISABLED",vars.proj_teale_albers) #@UndefinedVariable
    else:
        log.write("temporary feature class already exists - deleting",1)
        arcpy.Delete_management(temp_fc)
        
        
    l_point = arcpy.Point(lat,long,0,0,1) #lat, long,z,m,id
    
    # Open an insert cursor for the new feature class
    cur = arcpy.InsertCursor(temp_fc)
    
    new_feature = cur.newRow()
    new_feature.shape = l_point
    cur.insertRow(new_feature)
    
    temp_result = os.path.join(arcpy.env.workspace,"temp_result") #@UndefinedVariable
    
    arcpy.SpatialJoin_analysis(temp_fc,vars.HUCS,temp_result)
    
    # Create a search cursor 
    rows = arcpy.SearchCursor(temp_result) 
    for row in rows:
        HUC12_ID = row.getValue("HUC_12")
    
    log.write("HUC_12 ID found - %s\n" % HUC12_ID)
    
    try:
        print "deleting temporary feature classes..."
        arcpy.Delete_management(temp_fc)
        arcpy.Delete_management(temp_result)
    except:
        log.write("Unable to remove temporary feature classes",1)

    return HUC12_ID '''

def determine_certainty(certainties):
    for certainty in certainties: # step through them in order - return the first valid one
        if not certainty == None:
            return certainty
    else:
        raise vars.DataProcessingError("Unable to determine observation's certainty. Check to make sure that either the observation type or the IF_Method has a certainty assigned in the database (or ensure both do)")

def pull_alt_codes():
    global alt_codes_by_filter # we're using the shared variable
    
    l_cursor,l_conn = funcs.db_connect(vars.maindb,"Pulling Alt Codes")
        
    l_sql = "select Input_Filter,FID,Alt_Code from Alt_Codes order by Input_Filter asc"
    
    l_results = l_cursor.execute(l_sql)
    for row in l_results:
        l_alt_code = string.upper(row.Alt_Code) # make sure we're always comparing apples to apples
        if not alt_codes_by_filter.has_key(row.Input_Filter): # if this is the first one for this filter
            alt_codes_by_filter[row.Input_Filter] = {} # make the dictionary
        alt_codes_by_filter[row.Input_Filter][l_alt_code] = row.FID # set the key of the Alt_Code to the FID
        
    funcs.db_close(l_cursor,l_conn)

class Moyle_IF(Gen_Table_IF):
    def __init__(self,full_obs_set):
        self.all_init(full_obs_set)
        
        self.name_match_string = '^(.+?)poly.*$' # we want the part at the front before the poly 
        self.name_match_group = 1  
    
    #def process_observations(self):
        
        # the following would be the plan if this remained as a Gen_Poly_IF
        # 0) Save the original dataset path
        # 1) select by attributes the features with a particular certainty
        # 2) set a certainty value to feed into determine_certainty
        # 3) set the dataset path to the selected features
        # 4) call the selected features into the parent process_observations
        # 5) do it again for any other certainty levels
        # 6) reset the dataset path
        
    #    Gen_Table_IF.process_observations(self)
             
    def handle_certainty(self,item,observation,row,method):
        certainty_map = {1:2,2:2,3:3,4:2,5:3}
        
        if certainty_map.has_key(row.CONFIDENCE):
            return certainty_map[row.CONFIDENCE] # return our value for the certainty level that the layer provides
        else:
            return 3
    
    def determine_species(self):
        input_filter.determine_species(self,self.parent.dataset_name)
    
    def determine_species_for_record(self,junk): # override - it's the same for every observation in a Moyle_IF set
        return self.parent.species_fid
    
class R5_Table_IF(Gen_Table_IF):
    
    def __init__(self,full_obs_set):
        self.l_codes = {31:[1,1],32:[3,2],41:[1,1],42:[3,2]} # codes that tell us if they are present or not
        # each key is the codes for presence that the forest service has and the following list is Observation Type, Certainty
       
        # call the parent class' version - we just want to make sure that the codes get defined
        Gen_Table_IF.__init__(self, full_obs_set)
        
    def process_observations(self):
        
        print "Preprocessing %s" % self.parent.dataset_name
        
        # add the fields we'll use
        arcpy.AddField_management(self.parent.dataset_path,"Species","TEXT")
        arcpy.AddField_management(self.parent.dataset_path,"Mod_Flag","LONG")
        
        # copy the feature class to the calculations db. We'll read it from there so we can update the original
        out_name = os.path.join(vars.workspace,self.parent.dataset_name)
        arcpy.Copy_management(self.parent.dataset_path,out_name)
        
        # figure out which species are actually fields in this dataset
        species_fields = []
        l_fields = arcpy.ListFields(out_name)
        for field in l_fields: # we're going to loop over the fields and check if it's in the alt_codes. This way, we know which fields are used for species - we could theoretically just loop over the alt codes, but that assumes that all datasets for a particular filter have that column, and we might get an exception.
            if field.name in alt_codes_by_filter[self.parent.filter_code]:
                species_fields.append(field.name)
        
        # make the cursors
        try:
            l_dataset = arcpy.SearchCursor(out_name)
            l_insert = arcpy.InsertCursor(self.parent.dataset_path)
        except:
            raise vars.DataProcessingError("Unable to load cursors for dataset to preprocess")
        
        for row in l_dataset: # iterate over each row
            for column in species_fields: # and scan through each of the species columns
                
                #print "Row: %s, Column: [%s]" % (row,column)
                try:
                    if not (row.isNull(column) or row.getValue(column) == 0): # if that column has a value
                        new_row = l_insert.newRow()
                        new_row = copy_row(new_row, row, l_fields) # copies the values from the current row into the new row
                        new_row.setValue("Species",column) # set the species column to the alt_code - if this doesn't work, it might be because it's not an update cursor?
                        new_row.setValue("Mod_Flag",1) # set the mod_flag
                        l_insert.insertRow(new_row) # then copy the row over - this can happen multiple times for a given initial record so that we get all species
                except:
                    log.error("Skipping record - exception raised copying data over")
                    continue
                
        # close the tables
        del row
        del l_dataset
        del l_insert
        
        # call the parent class' version now that we've done our preprocessing
        Gen_Table_IF.process_observations(self)
    
    # we need to override these two handlers and inject a check before them since the certainty and observation type are determined in each record.
    def handle_obs_type(self, item, observation, row, method):
        
        if not (row.Species is None or row.Species == 0): # if the row has a species and
            if row.__dict__[row.Species] in self.l_codes.keys(): # if the value of that species' column is in the codes provided 
                return self.l_codes[row.__dict__[row.Species]][1]
            else: # call the parent class
                return Gen_Table_IF.handle_obs_type(self, item, observation, row, method)
    
    def handle_certainty(self, item, observation, row, method):
        
        if not (row.Species is None or row.Species == 0): # if the row has a species and
            if row.__dict__[row.Species] in self.l_codes.keys(): # if the value of that species' column is in the codes provided 
                return self.l_codes[row.__dict__[row.Species]][1]
            else: # call the parent class
                return Gen_Table_IF.handle_certainty(self, item, observation, row, method)
        
def copy_row(new_row,old_row,fields):
    for field in fields:
        if field.editable:
            new_row.setValue(field.name,old_row.getValue(field.name))
    
    return new_row