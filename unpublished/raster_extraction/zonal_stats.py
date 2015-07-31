import os
import sys
import traceback
import subprocess

import arcpy
from arcpy.sa import ZonalStatisticsAsTable

from code_library.common import geospatial #@UnresolvedImport
import config
import log


#old_vars = ["rch","aet","cwd","pet","snow","subl","stor"]
#all_vars = ["run","ppt","pck","tmax","tmin"]
# Check out the ArcGIS Spatial Analyst extension license

#raster_names = ["GFDL_A2","PCM_A2"]
#config_data_dir = os.path.join(os.getcwd(),"..","data_futures")

#inZoneData = os.path.join(os.getcwd(),"snmeadows_area.gdb","snmeadows_hucs")

def run_multi_zonal(zones_files,gdb,log_string = None,merge = False, zone_field = None):
	"""
	batches zonal stats across a set of rasters

	:rtype : list
	"""

	var_num = 0

	if zone_field:
		true_zone_field = zone_field
	else:
		true_zone_field = config.zone_field

	return_tables = [] # will become a list of lists unless merge is True, then it's just a list

	num_vars = len(gdb.rasters)
	for raster in gdb.rasters:
		var_num += 1
		zone_num = 0

		log.write("Switching Vars to %s - # %s" % (raster,var_num),True)

		zs_list = []

		for zone_file in zones_files:

			zone_num += 1

			if log_string:
				log.write("\n%s; raster %s of %s; feature %s" % (log_string,var_num,num_vars,zone_num),True)
			else:
				log.write("\nraster %s; feature %s" % (var_num,zone_num),True)

			try:
				outfile = zs_for_zonal(zone_file,gdb,raster,true_zone_field) # this was originally split out in order to accomodate point estimaes. Not necesary now

				if outfile and outfile == "continue": # a non-error signal sent up through the chain - this should
					# probably be done as some type of exception
					continue

				if outfile:
					zs_list.append(outfile)
			except:
				exception = traceback.format_exc()
				log.error("Failed to run zonal stats on raster %s in gdb %s - exception follows: %s" % (raster,gdb.name,exception))
				continue

		if merge:
			output_name = os.path.join(gdb.output_gdb,raster)
			output_merged = merge_zonal(zs_list,output_name)
			if output_merged:
				return_tables.append(output_merged)
		else:
			return_tables.append(zs_list)

	return return_tables

def zs_for_zonal(zone_file,gdb,raster,true_zone_field):
	"""
	Handles the calling and management of using zonal stats to obtain data for a polygon
	:rtype : str
	"""

	if config and config.check_zone_size:
		try:
			zone_size_ok = check_zone_size(zone_file,os.path.join(gdb.path,raster))
			if not zone_size_ok:
				log.error("checking raster size against feature looked like failure imminent. Skipping zone_file %s for raster %s" % (zone_file,raster))
				return "continue"
		except:
			log.error("checking raster size against feature looked like failure imminent. Skipping zone_file %s for raster %s" % (zone_file,raster))
			return "continue"

	full_raster = os.path.join(gdb.path,raster)

	if config.flag_subprocess_zonal_stats:
		try:
			# call this beforehand to minimize creation of tempdbs and parsing of the output
			outfile,filename,output_location,raster_name = get_output_table(full_raster,None,None)

			# the subprocessed version will return an appropriate status code. Only when it's 0 does outfile get set properly. Otherwise, an exception is raised
			t_outfile = subprocess_check_output([os.path.join(sys.prefix,"python.exe"),os.path.join(config.run_dir,"standalone_zonal.py"),zone_file,full_raster,true_zone_field,filename,output_location])
			t_info = t_outfile.split('\n') # there will be multiple output lines, so split it
			log.write("returned info says outfile at %s - we have it stored at %s. Those should match" % (t_info[-2],outfile)) # and get the last line
			del t_info # cleanup
		except CalledProcessError as e:
			log.error("Interpreter Crash - proceeding - error given: %s" % e)
			outfile = None
		except:
			err_str = traceback.format_exc()
			log.error("Other error in subprocessing. Proceeding, but something's wrong! error gave %s" % err_str)
			outfile = None
	else:
		# or, in a sane world, just call zonal_stats
		outfile = zonal_stats(zone_file,full_raster,true_zone_field)

	return outfile


def check_zone_size(zone_file,raster):
	log.write("Checking areas against each other...")

	area_field = 'Shape_Area'
	t_curs = arcpy.SearchCursor(zone_file,'','',area_field)
	for row in t_curs:
		shape_area = row.getValue(area_field)
		break # only do it once - we can use the cursor differently, but this speedup is negligable here

	if not shape_area:
		log.error("No area")
		return False

	raster_band_info = arcpy.Describe(os.path.join(raster,"Band_1"))
	cell_area = int(raster_band_info.meanCellWidth * raster_band_info.meanCellHeight)

	# this is a hack right now that does NOT account for differences in units. this WILL BREAK if the units are different. Turn it off in config if that's the case
	if cell_area > shape_area: # 
		ret_val = False
	else:
		ret_val = True

	del raster_band_info	
	del t_curs

	return ret_val


def merge_zonal(file_list,output_name):

	log.write("Merging tables",True)
	try:
		if arcpy.Exists(output_name): # doesn't seem to obey overwriteOutput in 10.0
			arcpy.Delete_management(output_name)

		# now run the merge
		arcpy.Merge_management(file_list,output_name)
	except:
		exception = traceback.format_exc()
		log.error("Couldn't merge - traceback follows: %s" % exception)
		return None

	return output_name

def zonal_stats(zones,raster,zone_field,filename = None, output_location = None,silent = False):

	try:
		# Set local variables
		out_table,filename,output_location,raster_name = get_output_table(raster,filename,output_location)

		try:
			if arcpy.Exists(out_table):
				if not silent:
					log.write("Skipping - already complete",True)
				return out_table
		except:
			if not silent or silent == "error":
				log.error("Couldn't test if it already exists...move along!")

		try:
			if not silent:
				log.write("Running Zonal",True)
			arcpy.env.extent = zones
			outZSaT = ZonalStatisticsAsTable(zones, zone_field, raster, out_table, "DATA", "ALL")
		except SystemExit:
			if not silent or silent == "error":
				log.error("System Exit returned from ZonalStatisticsAsTable")
		except:
			if not silent or silent == "error":
				log.error("Unable to run stats on raster %s" % out_table)
			return None

		del outZSaT # these should be local, but it's Arc!

		return out_table

	except:
		if not silent or silent == "error":
			log.error("Unhandled Exception in zonal_stats function")

def get_output_table(raster,filename=None,output_location=None):
	raster_name = os.path.splitext(os.path.split(raster)[1])[0]
	if filename is None or output_location is None:
		out_table = geospatial.generate_gdb_filename("xt_%s" % raster_name)

	return out_table,filename,output_location,raster_name # we may need all of this

def subprocess_check_output(*popenargs, **kwargs):
	r"""
	Nick took this directly from the Python 2.7 codebase and
	modified it only so that things properly reference the subprocess
	module. This is exactly the function we need, but it's not available in
	Python 2.6

	Run command with arguments and return its output as a byte string.

	If the exit code was non-zero it raises a CalledProcessError.  The
	CalledProcessError object will have the return code in the returncode
	attribute and output in the output attribute.

	The arguments are the same as for the Popen constructor.  Example:

	>>> check_output(["ls", "-l", "/dev/null"])
	'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

	The stdout argument is not allowed as it is used internally.
	To capture standard error in the result, use stderr=STDOUT.

	>>> check_output(["/bin/sh", "-c",
	...			   "ls -l non_existent_file ; exit 0"],
	...			  stderr=STDOUT)
	'ls: non_existent_file: No such file or directory\n'
	"""
	if 'stdout' in kwargs:
		raise ValueError('stdout argument not allowed, it will be overridden.')
	process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
	output, unused_err = process.communicate()
	retcode = process.poll()
	if retcode:
		cmd = kwargs.get("args")
		if cmd is None:
			cmd = popenargs[0]
		raise CalledProcessError(retcode, cmd, output=output)
	return output

class CalledProcessError(Exception):
	"""Also need a copy of this class because it has a new kwarg

	This exception is raised when a process run by check_call() or
	check_output() returns a non-zero exit status.
	The exit status will be stored in the returncode attribute;
	check_output() will also store the output in the output attribute.
	"""
	def __init__(self, returncode, cmd, output=None):
		self.returncode = returncode
		self.cmd = cmd
		self.output = output
	def __str__(self):
		return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)
