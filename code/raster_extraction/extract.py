__author__ = 'nrsantos'

import os

import join_tables
import zonal_stats
import support
import log
import config

def extract_data(zones=None, rasters=None, zone_field=config.zone_field, use_point_estimate=False):
	# loads the input data
	support.setup(zones)

	if use_point_estimate:
		support.point_estimate(zones, rasters)
	else:
		main_zonal(zones, rasters, zone_field,)


def main_zonal(zones=None, rasters=None, zone_field=None, ):

	# splits the polygons and creates the objects
	input_dataset = support.polygon_file(zones)

	log.write("Running Zonal Stats", True)
	# does the actual running and merging of the zonal stats
	tables = support.run_files([input_dataset], rasters)

	log.write("Joining tables into master output table")

	try:
		joiner = join_tables.join_data
		joiner.tables = tables
		joiner.join_field = zone_field
		joiner.add_fields = ["SUM", "MEAN"]

		joiner.join()
	except:
		# if we make it this far, it'd be nice to save this data structure
		import shelve
		shelf_name = os.path.join(config.run_dir,"zonal_stats_dump.shelf")
		object_cache = shelve.open(shelf_name)
		object_cache["data"] = tables
		object_cache.sync()

		log.error("Unhandled exception raised in joiner - dumped the zonal stats table into object shelf in the run directory")

