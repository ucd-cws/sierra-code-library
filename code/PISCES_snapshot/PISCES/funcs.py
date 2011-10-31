import arcpy, vars, os, log, pyodbc, sys #@UnresolvedImport - eclipse flag to ignore that it can't seem to find pyodbc
import re, string
import observations, input_filters

def db_connect(db_name, note = None):
        # we're making this a function because we do want to close
        # the db after every statement in case ARC needs to access it
        # in between our own accesses
        
    log_string = "Making database connection to %s" % db_name
        
    if not note == None:
        log_string += " - note added: %s" % note
            
    log.write(log_string)
    conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb)};DBQ='+db_name)
    return conn.cursor(),conn


def db_close(cursor,conn):
    log.write("Closing database connection")
    cursor.close()
    conn.close()

def data_stats():
    import numpy
    
    print "\nCalculating data stats" 
    
    total_records_sql = "select Count (*) from observations"
    total_fish_w_data_sql = "select Count(*) from (select distinct Species_ID from Observations)"
    
    # pop the info for each fish into a numpy array (numpy.array([0,1,2...]) and then print out numpy.sum() numpy.std() numpy.mean() for the natives
    
    print "No stats yet - add this"
    
    
    
    
def new_data_get_current_observation_sets(l_connection): #get_current_data
    l_sql = 'SELECT Source_Data FROM Observation_Sets;'
    l_cursor,l_conn = db_connect(vars.maindb)
    
    l_connection.append(l_cursor)
    l_connection.append(l_conn)
    
    l_data = l_cursor.execute(l_sql)
    
    return l_data
    
def new_data_fetch():
    log.write("\nChecking for new data in %s" % vars.newdb,1)

    new_data_pull() # fetches the rows from the database that correspond to the feature sets we're about to fetch
    new_data_validate()
    new_data_dedupe() # dedupe also sets up the observation set for each item if it's not a duplicate
   
def new_data_validate():
    log.write("Ensuring new data rows have a corresponding dataset")
    
    arcpy.env.workspace = vars.newdb
    
    for new_data in vars.input_rows.keys(): # if a record in the database leads to a feature class that doesn't exist, remove it from the list to process
        if not arcpy.Exists(new_data):
            log.error("Skipping %s - No feature class exists for database row" % new_data)
            del vars.input_rows[new_data]
    else:
        log.write("All database records have a corresponding dataset")
                
    arcpy.env.workspace = vars.workspace #set the workspace back!
            

def new_data_dedupe(): # simply checks them against existing observations to warn if we are duplicating
    log.write("Checking new datasets for duplicates") 
    l_connection = [] #this construction is stupid - it should be changed at some point, but not right now.
    
    l_existing_data = new_data_get_current_observation_sets(l_connection) # Check for redundant features - l_connection passed in so the db connection can be placed in it
   
    for item in vars.input_rows.keys(): #for each item in the list of features
        for existing_data in l_existing_data:
            if(existing_data == item): # check it against the list of existing data in the db
                log.write("Feature class %s is the same as %s - if you believe them to be different, please rename the new feature class" % (vars.input_rows[item],existing_data),1)
                del vars.input_rows[item]               # if if already exists, remove it from the array
                break                                   # and go to the next iteration
            
        print "New Feature Class: %s\n" % item
        
        l_dataset = vars.observation_set(os.path.join(vars.newdb,item),item) #__init__ takes the dataset path as an optional argument
        vars.datasets.append(l_dataset)
    
    db_close(l_connection[0],l_connection[1])
    del l_connection #clean up - this program could run a while and we want it clean
    
    #### Returning
    arcpy.env.workspace = vars.workspace
        #switch the workspace back
    
    
def new_data_pull():
    log.write("Checking %s for new data" % vars.newdb)
    l_cursor,l_conn = db_connect(vars.newdb)
    l_sql = 'SELECT ID,Feature_Class_Name,Species_ID,Input_Filter,Presence_Type,IF_Method,Observer_ID,Survey_Method,Notes,Data_Source_Notes,Input_Filter_Args, Projection FROM NewData where Imported = 0 order by Species_ID asc;'
    
    l_data = l_cursor.execute(l_sql)
    for row in l_data:
        vars.input_rows[row.Feature_Class_Name] = vars.input_data(row.ID,row.Species_ID,row.Input_Filter,
                                                              row.Presence_Type,row.IF_Method,
                                                              row.Observer_ID,row.Survey_Method,row.Notes,row.Data_Source_Notes,
                                                              row.Input_Filter_Args,row.Projection)
        log.write("Found data %s in input database" % row.Feature_Class_Name)
    
    db_close(l_cursor,l_conn)

def setup_new_data(obs_sets):
    for key in range(len(obs_sets)): #doing this with the index values so that we can delete it if we need to.
        try:
            obs_sets[key].setup(key) #passing in key so that errors can be handled in the function
        except vars.DataProcessingError as error_msg:
            obs_sets[key] = None # if we get an error processing the data while setting it up, remove it from the array to skip it, but then continue - it won't be processed in the future.
                            # we use = None instead of del so that the array doesn't get reindexed.
                            # TODO: This solution doesn't address the problem of previously committed data.
            log.write(error_msg,1)
   
   
def get_species_from_alt_code(l_alt_code_species, filter_code):
    
    l_alt_code_species = string.upper(l_alt_code_species) # standardize everything coming in - they alt codes are indexed in caps
    
    if input_filters.alt_codes_by_filter.has_key(filter_code) and input_filters.alt_codes_by_filter[filter_code].has_key(l_alt_code_species): # if the input filter has alt codes and this alt code is defined
        return input_filters.alt_codes_by_filter[filter_code][l_alt_code_species]
    else:
        return False

def copy_data(feature_class, new_location): # get a full path and a place to copy it to, defaulting to the observations database

    l_file_split = os.path.split(feature_class)
    out_name = l_file_split[1]
    
    inc = 0
    return_flag = 0
    while arcpy.Exists(os.path.join(new_location,out_name)): # if the name already exists in the output location, start renaming it with an iterator until we reach one that doesn't
        inc = inc + 1
        out_name = "%s_%02i" %(out_name[:-3],inc)
        return_flag = 1
    
    arcpy.Copy_management(feature_class,os.path.join(new_location,out_name))
    log.write("Saving %s to %s" % (feature_class,new_location))
    
    if return_flag == 1: # we need to send back the new name
        return out_name

def clean_workspace(): # gets a list of all of the feature classes in the workspace and removes them all
    
    log.write("Cleaning workspace")
        
    if arcpy.Exists(vars.workspace): # if we have a workspace, clean it out
        arcpy.env.workspace = vars.workspace #set arcpy's workspace to our own in case it isn't
        l_all_fc = arcpy.ListFeatureClasses()
        for item in l_all_fc:
            try:
                arcpy.Delete_management(os.path.join(arcpy.env.workspace,item)) #@UndefinedVariable
            except:
                log.write("Unable to clean workspace - close all ESRI Software")
                raise vars.GenError("Unable to clean workspace - cannot proceed - please close all ESRI Software")
    else: # if we don't have a workspace, create the file. It'd be bad to assume it exists if it didn't
        workspace_parts = os.path.split(vars.workspace)
        arcpy.CreatePersonalGDB_management(workspace_parts[0],workspace_parts[1])

def setup_test_mode(): # test mode lets us simulate the script, but copies the datafiles to new ones and uses those
    #                    this lets us simulate an import before conducting it, etc
    
    import string
    import shutil
    log.write(auto_print=1, log_string="Running in test mode. Copying data files - this may take some time...")

    #make the path for test mode
     
    try:
        test_path = vars.test_folder
        log.write("Checking for test folder and replacing old test files")
        
        if not os.path.exists(test_path): # if the test folder doesn't exist
            os.makedirs(test_path) # make it!
        
    except:
        log.write(log_string="Unable to start in test mode - couldn't make the test directory - exiting", auto_print=1)
        raise
    
    #copy dbs and set new path
    l_folders = ["data","inputs","log","maps","mxds","proc"]
    l_exclude = ["Hillshade","data_storage","maps","output","temp.gdb"] # having maps here too will create the folder structure but not move the data
    for index in range(len(l_folders)): # make a listing of the main folders we want to copy - this new method will be slower since it only checks the mod time on the folders and not the files
        l_folders[index] = os.path.join(vars.internal_workspace,l_folders[index])
    
    # if this ends up being slow, it would probably be relatively quick for us to iterate over the files IN each of the folders we name above (if it has files, in this case they all do)
    # and then check for modified data there before copying

    
    for folder in l_folders:
        m_folder = string.replace(folder,vars.internal_workspace,test_path)
        if not os.path.exists(m_folder):
            os.mkdir(m_folder)
        
        try:  #before copying files, see if it has been modified. If it has, remove the old one and add the new one.
            l_data = os.walk(folder)
            
            for i_folder in l_data: # this will iterate over every folder, subfolder, etc
                  
                folder_base = i_folder[0]
                new_folder_base = folder_base

                new_folder_base = string.replace(new_folder_base,vars.internal_workspace,test_path)
                if new_folder_base[-1:] == "\\": # chop off the trailing slash
                    new_folder_base = new_folder_base[:-1]
                    
                for subfolder in i_folder[1]: # folder[1] will hold this folder's own subfolder - make the folders
                    new_folder = os.path.join(new_folder_base,subfolder)
                    if not os.path.exists(new_folder):
                        os.mkdir(new_folder)

                continue_flag = 0 # skip this folder if it's in our skip list, but only AFTER we've created the subfolders - we always want the tree, but we might not want the items.
                for exclude_item in l_exclude: # skip these items though
                    if not (re.search(exclude_item,i_folder[0]) == None):
                        continue_flag = 1
                        
                    #print i_folder[0]
                if continue_flag == 1: # structured this way to break out of the outer loop
                    continue


                for file in i_folder[2]: # copy all the files over
                    old_path = os.path.join(folder_base,file)
                    new_path = os.path.join(new_folder_base,file)
                    
                    l_mtime1 = int(os.path.getmtime(old_path)) # get the modified time
            
                    l_new_file_exists = os.path.exists(new_path) #rather than call it twice, store the result
                    if l_new_file_exists:
                        l_mtime2 = int(os.path.getmtime(new_path))
                    else: # it doesn't exist yet
                        l_mtime2 = 0 # set it, but it won't be equal, so it'll copy in the next step
        
                    if l_new_file_exists and l_mtime1 == l_mtime2 : # if it already exists in the test folder AND the files were modified at the same time
                        pass #they're the same! Awesome - don't do anything
                    else: #otherwise, we need to change some things
                        if l_new_file_exists:
                            os.remove(new_path) # same story - out with the old
                        shutil.copy2(old_path,new_path) # create a new one
                                
        except:
            log.write("Unable to start in test mode - couldn't copy the folder %s - exiting" % folder, 1)
            raise # raise this exception up

    vars.set_workspace_vars(test_path) # resets them all with test_path as the base
            
   
def remove_data(item_name, l_workspace = arcpy.env.workspace): # checks if a feature exists, then deletes it @UndefinedVariable
    t_wkspc_save = arcpy.env.workspace #@UndefinedVariable
    
    arcpy.env.workspace = l_workspace # get the workspace of the function calling this so we remove the correct item
    # this should actually be carried across functions...should use the same workspace as before.
    
    if arcpy.Exists(item_name): # if it exists
        arcpy.Delete_management(item_name) # delete it
    
    arcpy.env.workspace = t_wkspc_save
    
def is_between(check_num,num1,num2): # checks whether check_num is between num1 and num2 without assumptions of the sign of num1 or num2 since a max in ArcGIS could be in a different quadrant from the min
    
    if check_num < num1 and check_num > num2:
        return True
    if check_num > num1 and check_num < num2:
        return True
    
    return False