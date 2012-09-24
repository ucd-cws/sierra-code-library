import os
import sys

import arcpy

import join_tables
import zonal_stats
import support 
import log
import config

def main_zonal():

	# splits the polygons and creates the objects
	input_dataset = support.polygon_file(config.input_dataset)

	log.write("Running Zonal Stats",True)
	# does the actual running and merging of the zonal stats
	tables = support.run_files([input_dataset],config.datasets)

	log.write("Joining tables into master output table")

	try:
		joiner = join_tables.join_data
		joiner.tables = tables
		joiner.join_field = config.zone_field
		joiner.add_fields = ["SUM","MEAN"]

		joiner.join()
	except:
		# if we make it this far, it'd be nice to save this data structure
		import shelve
		shelf_name = os.path.join(config.run_dir,"zonal_stats_dump.shelf")
		object_cache = shelve.open(shelf_name)
		object_cache["data"] = tables
		object_cache.sync()

		log.error("Unhandled exception raised in joiner - dumped the zonal stats table into object shelf in the run directory")


if __name__ == '__main__': # used in case of multiprocessing
	
	# loads the input data
	support.setup(config.input_dataset)
	
	if config.use_point_estimate:
		support.point_estimate(config.input_dataset,config.datasets)
	else:
		main_zonal()


