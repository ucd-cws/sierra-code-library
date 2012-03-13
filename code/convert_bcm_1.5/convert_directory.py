import arcpy, os, sys

config_parent_folder = r""
config_vars = []
config_years = []

log_out_file = open(os.path.join(os.getcwd(),"log.txt"),'w')
run_dir = os.getcwd()

def log(msg):
    print msg

    global log_out_file
    
    log_out_file.write(msg)

log("\n\n\n\nBegan run")

for var in vars:


l_input = os.path.join(config_parent_folder,"snow")


l_output = os.path.join(run_dir,"converted_snow.gdb") #always set an output folder
#if not os.path.exists(l_output): # if it doesn't exist, make it
#	os.mkdir(l_output)

# make the var for all of the intermediary files
l_temp = os.path.join(l_dir,"temp.gdb")
	
if coverage_flag == None: # if it wasn't passed, assume it's not a coverage - this would be better accomplished with an arcpy directive to understand the type of the dataset. Feel free to add this in (ListDatasets can filter by type of dataset)
	coverage_extra = ""
else: # if anything was set in that space, set it to look for the polygon component of the coverage
	log( "Looking for coverages!")
	coverage_extra = "\\polygon"

log( "Looking for data in %s" % l_input)
arcpy.env.workspace = l_input # set the workspace for arcpy to look in
log( "WARNING: Output will be overwritten if it exists...")
arcpy.env.overwriteOutput = True #make arcpy overwrite existing datasets instead of crashing

#dir_list = os.listdir(l_input) # use this if listdatasets doesn't bring anything up (extension differences, etc) - then comment out the next line
dir_list = arcpy.ListDatasets() # checks arcpy.env.workspace for arc datasets

log( "Processing %s Items" % len(dir_list))

errors = False #set the flag to false - it'll be set to true if there was an error

num_total = len(dir_list)

for item in dir_list: # for EVERY arc item in the directory
        print "%s left!" % num_total
        num_total -= 1
        
        new_name = item[:-4] # slices off the extension - we'll be putting the rasters in gdbs
	in_file = os.path.join(l_input,item) # make a compatible input string for the filename
	in_file = in_file + coverage_extra # this makes all the os.path.join work a little futile...but it will append what we need to access coverages if that's set
	out_file = os.path.join(l_output,new_name)
	out_intermediate = os.path.join(l_temp,new_name)
	projection = os.path.join(l_dir,"TealeAlbers.prj") # we want to project to TealeAlbers
        
	log( "\nProcessing %s" % in_file)
	try:
		try:
			log( "Converting to raster")
			arcpy.ASCIIToRaster_conversion(in_file,out_intermediate, "INTEGER")
		except:
			log( "Couldn't convert to raster --- from %s to %s" %(in_file,out_intermediate))
			raise #let it get caught above so it gets skipped and has a stack trace printed
		try:
			log( "Defining projection")
			arcpy.DefineProjection_management(out_intermediate, os.path.join(l_dir,"PROJCS['NAD_1983_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-96.0],PARAMETER['Standard_Parallel_1',29.5],PARAMETER['Standard_Parallel_2',45.5],PARAMETER['Latitude_Of_Origin',23.0],UNIT['Meter',1.0]]"))
		except:
			log( "Couldn't define projection")
			raise #let it get caught above so it gets skipped and has a stack trace printed
		try:
			log( "Projecting")
			arcpy.ProjectRaster_management(out_intermediate,out_file,projection)
		except:
			log( "Couldn't project")
			raise #let it get caught above so it gets skipped and has a stack trace printed

		try:
			log( "Deleting temporary file") # save the disk space
			arcpy.Delete_management(out_intermediate)
		except:
			log( "Couldn't delete")
	except: # well crap, we hosed it somewhere
		errors = True
		import traceback
		log( "unable to process file")
		log( '-'*60) # print a line to the terminal
		traceback.print_exc() # print a stacktrace and exception info
		log( '-'*60) # print a line to the terminal
		log( "\n\n\n")
		continue # and then move on with our lives - go to the next iteration of the loop (don't crash)

log( "\n\n")
if errors == True:
	log( "Errors occurred during processing of at least one dataset - scroll up to find out")
log( "All files complete")
raw_input("Press Enter to close...")
