import os
import sys
import shutil

import arcpy

# important setting - don't change unless you know what you're doing
run_dir = os.getcwd()

# Configuration settings - feel free to change them, but you should also probably know what you're doing here.
# The code may not check for exceptions related to bad settings here
config_parent_folder = r"E:\CEC\bcm_data\compressed_raw"
config_network = False # set to true if the .asc files (as set in config_parent_folder) are on a network location. The script will then take steps to minimize network time to speed things up
config_vars = ["run","rch","ppt","pck","tmin","tmax","aet","cwd","pet","snow","subl","stor"]
config_years = range(1890,2150)
config_temp_dir = os.path.join(run_dir,"temp")
arcpy.env.overwriteOutput = True # make arcpy overwrite existing datasets instead of raising an exception

config_projection = os.path.join(run_dir,"TealeAlbers.prj") # we want to project to TealeAlbers
config_bcm_prj = "PROJCS['NAD_1983_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-96.0],PARAMETER['Standard_Parallel_1',29.5],PARAMETER['Standard_Parallel_2',45.5],PARAMETER['Latitude_Of_Origin',23.0],UNIT['Meter',1.0]]"

# log file names
log_out_file = open(os.path.join(os.getcwd(),"log.txt"),'w')
error_log = open(os.path.join(os.getcwd(),"errors.txt"),'w')

# setup variables
flag_errors = False #set the flag to false - it'll be set to true if there was an error

temp = os.path.join(run_dir,"temp.gdb")
months = ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec",)

# basic functions
def log(msg):
    print msg

    global log_out_file
    
    log_out_file.write(msg)

def file_failed(filename,msg):
	global error_log
	
	global flag_errors
	
	flag_errors = True
	error_log.write("Failed to process file: %s - %s" % (filename,msg))
	
	log(msg)

def network_copy(input_file):
	filename = os.path.split(input_file)[1]
	new_name = os.path.join(config_temp_dir,filename)
	try:
		shutil.copy2(input_file, new_name)
	except:
		file_failed(input_file,"failed to copy file over the network to local location")
		return None
	
	return new_name

def network_clean(filename):
	try:
		os.remove(filename)
	except:
		log("Unable to delete temporary file %s from temp folder - non-critical - continuing on!" % filename)

def year_in_range(filename):
	
	if len(config_years) > 0:
		filter_found = False
		for filter_string in config_years:
			if filename.find(str(filter_string)) > -1:
				return True
		if filter_found is False:
			log( "Filter not found - skipping table" )
			return False # go to the next table

def check_gdb(folder,gdb_name):
	if not arcpy.Exists(gdb_name):
		try:
			log("Creating %s" % gdb_name)
			arcpy.CreateFileGDB_management(folder,gdb_name)
		except:
			file_failed(gdb_name,"Unable to create output geodatabase, and it doesn't exist - skipping entire variable!")
			return False
	return True

def standardize_name(var,filename):
	'''converts all filenames to a single, common format that makes them sortable and orders them in megatables, etc'''
	year = None
	month = None
	if len(config_years) > 0:
		for filter_string in config_years:
			if filename.find(str(filter_string)) > -1:
				year = filter_string
		for filter_string in months:
			if filename.find(str(filter_string)) > -1:
				month = filter_string
		if year and month:
			return "%s_%s_%s" %(var,year,month)
		else:
			return filename
		
	else:
		return filename

log("\n\nBegan processing")

if not os.path.exists(config_parent_folder):
	file_failed(config_parent_folder,"config_parent_folder is undefined or does not exist")

for var in config_vars:
	
	log("Switching to variable %s" % var)
	
	l_output_gdb = os.path.join(run_dir,"converted_%s.gdb" % var) #always set an output folder
	
	if check_gdb(run_dir,"converted_%s.gdb" % var) is False: # tries to make it and returns False on failure
		continue
	
	l_input = os.path.join(config_parent_folder,var)
		
	if not os.path.exists(l_input):
		file_failed(l_input,"input directory doesn't exist")	
	
	log("Looking for data in %s" % l_input)
	arcpy.env.workspace = l_input # set the workspace for arcpy to look in
	
	dir_list = arcpy.ListDatasets() # checks arcpy.env.workspace for arc datasets
	
	log( "Processing %s Items" % len(dir_list))
		
	num_total = len(dir_list)
	
	for item in dir_list: # for EVERY arc item in the directory
		print "%s left!" % num_total
		num_total -= 1

		if not year_in_range(item):
			continue # log message printed in function

		new_name = item[:-4] # slices off the extension - we'll be putting the rasters in gdbs
		in_file = os.path.join(l_input,item) # make a compatible input string for the filename
		std_name = standardize_name(var,new_name)
		out_file = os.path.join(l_output_gdb,std_name) # make this the new name
		out_intermediate = os.path.join(temp,new_name) # leave this as "new_name" so it can be traced to the input if it's left behind
		
		log( "\nProcessing %s" % in_file)
		
		if arcpy.Exists(out_file): # resume support if it crashes or needs to be stopped
			log("Skipping file - %s already exists" % out_file)
			continue
		
		if config_network is True:
			in_file = network_copy(in_file) # copy the file to local and replace in_file with the location
			if in_file is None:
				continue # means an error occurred - skip it
	    
		try:
			try:
				log( "Converting to raster")
				arcpy.ASCIIToRaster_conversion(in_file,out_intermediate, "FLOAT")
			except:
				log( "Couldn't convert to raster --- from %s to %s" %(in_file,out_intermediate))
				raise #let it get caught above so it gets skipped and has a stack trace printed
			try:
				log( "Defining projection")
				arcpy.DefineProjection_management(out_intermediate, config_bcm_prj)
			except:
				log( "Couldn't define projection")
				raise #let it get caught above so it gets skipped and has a stack trace printed
			try:
				log( "Projecting")
				arcpy.ProjectRaster_management(out_intermediate,out_file,config_projection)
			except:
				log( "Couldn't project")
				raise #let it get caught above so it gets skipped and has a stack trace printed
	
			try:
				log( "Deleting temporary file") # save the disk space
				arcpy.Delete_management(out_intermediate)
			except:
				log( "Couldn't delete")
		except: # well crap, we hosed it somewhere
			flag_errors = True
			import traceback
			log( "unable to process file")
			log( '-'*60) # print a line to the terminal
			traceback.print_exc() # print a stacktrace and exception info
			log( '-'*60) # print a line to the terminal
			log( "\n\n\n")
			continue # and then move on with our lives - go to the next iteration of the loop (don't crash)

		if config_network is True:
			network_clean(in_file) # just deletes the temp

log( "\n\n")
if flag_errors == True:
	log( "Errors occurred during processing of at least one dataset - scroll up to find out")
log( "All files complete")
raw_input("Press Enter to close...")
