import arcpy, os, sys
import vars, args, log
import funcs

#set up the workspace
log.initialize()
args.check_args()
vars.print_workspace_vars();
vars.data_setup() # populates variables with data from the database
#funcs.clean_workspace() #make sure that old data files are cleared out
funcs.data_stats()


### Process Any New Data ###
if vars.maponly == 0: # if we're not supposed to only map
    print "BEGINNING NEW DATA PROCESSING"
    
    funcs.new_data_fetch() # checks for new data, validates that it exists, and puts the info in the right spots
    funcs.setup_new_data(vars.datasets)
    
    #tried to implement multiprocessing here, but due to ESRI file locks, it will probably require significant refactoring of input filters and how they hold data to work, if it's possible. Not worth it now. May be someday, but unlikely. Sad face... Would have been pretty cool to have this thing scream through some datasets!
    
    for set in vars.datasets: # now that the datasets are loaded process them!
        if not set == None: # it's possible we've zeroed it out if it was an invalid dataset
            set.process_data() # will call the input filter for each dataset to handle the importing, then call cleanups
    
    db_cursor,db_conn = funcs.db_connect(vars.maindb,"Inserting results!") #open the db!
    
    log.write("\nInserting new records!",1)
    
    for set in vars.datasets:
        if not set == None: # TODO: Handle DataStorageErrors when thrown - we'll need to roll back a lot of things depending upon where they were thrown (call dataset.cleanup(), then zero it out)
            set.record_data(db_cursor)
            
    db_conn.commit() # if we've made it this far, hit the save key!
    funcs.db_close(db_cursor,db_conn) # close that sucker

    funcs.data_stats()
    
    
if vars.importonly == 0: # if we're not supposed to only import data
    ## MAPPING
    import mapping
    try:
        mapping.begin("all")
    except vars.MappingError as error:
        print "Uncaught error encountered while mapping - program provided: %s" % error

print "\nComplete"