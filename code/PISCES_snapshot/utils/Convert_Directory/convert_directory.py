import arcpy, os, sys

l_dir = "" # set defaults
coverage_flag = None

try:
        l_dir = sys.argv[1] # get the directory to use
        coverage_flag = sys.argv[2]
except:
        print "Arguments missing - that's ok, so long as you aren't trying to change input dirs or convert coverages - if you are, hit Ctrl+C and check what's going on\n\n"
        pass # we don't actually care 

if l_dir == None or l_dir == "": # if we don't have a directory - check for an empty string too because maybe someone just wanted to set the coverage flag too
	import string
	l_dir = string.replace(l_dir,'"','');
	l_dir = string.replace(l_dir,"'",""); # replace any quotes wrapped around the arg - this might have been done for us...if not, there's probably a better way to do this, but I'm not looking it up right now
	l_dir = os.getcwd() # if we weren't passed an argument, use the current folder
	l_input = os.path.join(l_dir,"input")
else: # we'll still need to set the inpu
	l_input = l_dir
	
l_output = os.path.join(l_dir,"converted.gdb") #always set an output folder
if not os.path.exists(l_output): # if it doesn't exist, make it
	os.mkdir(l_output)

# make the var for all of the intermediary files
l_temp = os.path.join(l_dir,"temp.gdb")
	
if coverage_flag == None: # if it wasn't passed, assume it's not a coverage - this would be better accomplished with an arcpy directive to understand the type of the dataset. Feel free to add this in (ListDatasets can filter by type of dataset)
	coverage_extra = ""
else: # if anything was set in that space, set it to look for the polygon component of the coverage
	print "Looking for coverages!"
	coverage_extra = "\\polygon"

print "Looking for data in %s" % l_input
arcpy.env.workspace = l_input # set the workspace for arcpy to look in
print "WARNING: Output will be overwritten if it exists..."
arcpy.env.overwriteOutput = True #make arcpy overwrite existing datasets instead of crashing

dir_list = arcpy.ListDatasets() # checks arcpy.env.workspace for arc datasets

print "Processing %s Items" % len(dir_list)

errors = False #set the flag to false - it'll be set to true if there was an error

for item in dir_list: # for EVERY arc item in the directory
        new_name = item[:-4] # slices off the extension - we'll be putting the rasters in gdbs
	in_file = os.path.join(l_input,item) # make a compatible input string for the filename
	in_file = in_file + coverage_extra # this makes all the os.path.join work a little futile...but it will append what we need to access coverages if that's set
	out_file = os.path.join(l_output,new_name)
	out_intermediate = os.path.join(l_temp,new_name)
	projection = os.path.join(l_dir,"TealeAlbers.prj") # we want to project to TealeAlbers
        
	print "\nProcessing %s" % in_file
	try:
                try:
                        print "Converting to raster"
        		arcpy.ASCIIToRaster_conversion(in_file,out_intermediate, "FLOAT")		
                except:
                        print "Couldn't convert to raster --- from %s to %s" %(in_file,out_intermediate)
                        raise #let it get caught above so it gets skipped and has a stack trace printed
                try:
                        print "Defining projection"
                        arcpy.DefineProjection_management(out_intermediate, "PROJCS['NAD_1983_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['False_Easting',0.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-96.0],PARAMETER['Standard_Parallel_1',29.5],PARAMETER['Standard_Parallel_2',45.5],PARAMETER['Latitude_Of_Origin',23.0],UNIT['Meter',1.0]]")
                except:
                        print "Couldn't define projection"
                        raise #let it get caught above so it gets skipped and has a stack trace printed
                try:
                        print "Projecting"
        		arcpy.ProjectRaster_management(out_intermediate,out_file,projection)
                except:
                        print "Couldn't project"
                        raise #let it get caught above so it gets skipped and has a stack trace printed
	except: # well crap, we hosed it somewhere
                errors = True
		import traceback
		print "unable to process file"
		print '-'*60 # print a line to the terminal
		traceback.print_exc() # print a stacktrace and exception info
		print '-'*60 # print a line to the terminal
		print "\n\n\n"
		continue # and then move on with our lives - go to the next iteration of the loop (don't crash)

print "\n\n"
if errors == True:
        print "Errors occurred during processing of at least one dataset - scroll up to find out"
print "All files complete"
raw_input("Press Enter to close...")
