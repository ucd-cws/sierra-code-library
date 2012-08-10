import arcpy
from arcpy import env
from arcpy.sa import *
import os

log_out_file = None

old_vars = ["rch","aet","cwd","pet","snow","subl","stor"]
all_vars = ["run","ppt","pck","tmax","tmin"]
# Check out the ArcGIS Spatial Analyst extension license
arcpy.CheckOutExtension("Spatial")


scenarios = ["GFDL_A2","PCM_A2"]
config_data_dir = os.path.join(os.getcwd(),"..","data_futures")

inZoneData = os.path.join(os.getcwd(),"snmeadows_area.gdb","snmeadows_hucs")
zoneField = "HUC_12"

def log(msg):
	print msg
	log_out_file
	log_out_file.write("%s\n" % msg)

def check_gdb(folder,gdb_name):
	if not arcpy.Exists(gdb_name):
		try:
			log("Creating %s" % gdb_name)
			arcpy.CreateFileGDB_management(folder,gdb_name)
		except:
			file_failed(gdb_name,"Unable to create output geodatabase, and it doesn't exist - skipping entire variable!")
			return False
	return True

def file_failed(filename,msg):
	global error_log
	
	global flag_errors
	
	flag_errors = True
	error_log.write("Failed to process file: %s - %s" % (filename,msg))
	
	log(msg)
	
var_num = 0

for scenario in scenarios:

        print "Switching scenarios to %s" % scenario
        data_folder = os.path.join(config_data_dir,scenario)
        
        for bcm_var in all_vars:

                if log_out_file is not None:
                        log_out_file.close()
                log_out_file = open(os.path.join(os.getcwd(),"zonal_stats_log_%s.txt") % bcm_var,'w')

                var_num += 1   
                log("Switching Vars to %s - # %s" % (bcm_var,var_num))

                # Set environment settings
                arcpy.env.workspace = os.path.join(data_folder,"converted_%s.gdb" % bcm_var )

                out_workspace = os.path.join(os.getcwd(),"zonal_%s_%s.gdb" % (bcm_var,scenario))
                if check_gdb(os.getcwd(),"zonal_%s_%s.gdb" % (bcm_var,scenario)) is False:
                        continue

                #num_hucs = arcpy.GetCount_management(inZoneData).getOutput(0)

                all_rasters = arcpy.ListRasters()

                num_left = len(all_rasters)
                num_processed = 0

                try:
                        for item in all_rasters:
                                log("\nvar %s -- %s left to process -- %s already processed" % (var_num,num_left,num_processed))
                                num_left -= 1
                                num_processed += 1
                                
                                log("processing %s" % item)

                                # Set local variables
                                outTable = os.path.join(out_workspace,"%s" % item)

                                try:
                                        if arcpy.Exists(outTable):
                                                log("Skipping - already complete")
                                                continue
                                except:
                                        log("Couldn't test if it already exists...move along!")

                                try:
                                        outZSaT = ZonalStatisticsAsTable(inZoneData, zoneField, item, outTable, "NODATA", "MIN_MAX_MEAN")
                                except SystemExit:
                                        log("System Exit returned from ZonalStatisticsAsTable")
                                except:
                                        #raise
                                        log("Unable to run stats on raster %s" % outTable)
                                        continue

                                try:
                                        pass
                                        #out_records = arcpy.GetCount_management(outTable).getOutput(0)
                                        #if not out_records == num_hucs:
                                        #        log("***** WARNING ******\nNUMBER OF RECORDS IN OUTPUT NOT EQUAL TO NUMBER OF ZONES\n***********************\n")
                                        #else:
                                        #        log("Number of records ok!")
                                except:
                                        log("Couldn't count records")
                                
                                try:
                                        del outZSaT # these should be local, but it's Arc!
                                        del outTable
                                except:
                                        log("couldn't delete stored values")
                except:
                        raise
                        log("Unhandled Exception")
                        
                
print "zonal stats completed!"
print arcpy.GetMessages()
