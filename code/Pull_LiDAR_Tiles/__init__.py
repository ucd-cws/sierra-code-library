__author__ = 'nrsantos'

"""
	Given a feature class that contains tile indices for lidar datasets and a root folder for those lidar data, this script copies out the lidar data to a specified folder
	It was written for the CVFED data but may accommodate other LiDAR datasets
"""

import os
import shutil

import arcpy

pull_folder = r"G:\Initial_LiDAR"  # The root folder to look for the tiles in
output_folder = r"E:\Home\nrsantos\CVFED"  # the folder to copy the tiles out to
tiles_fc = r"E:\Users\sunrsantos\Desktop\CVFED\drew_tiles.shp"  # The feature class that contains the tile indices
tiles_field = "TILE"  # The field in that feature class that indicates the tile name
tiles_ext = "5k.asc"  # The extension to look for on the tiles


def copy_out(out_tile, out_path, out_folder):
	try:
		shutil.copyfile(os.path.join(out_path, out_tile), os.path.join(out_folder, out_tile))
	except:
		print "Unable to copy tile %s" % out_tile
		raise


def read_tiles(fc, field, ext):
	tiles_cursor = arcpy.SearchCursor(fc, "", "", field)
	tiles = []

	for record in tiles_cursor:
		l_tile = record.getValue(field)
		if l_tile is not None:
			tiles.append(l_tile + ext)

	print "%s tiles requested" % len(tiles)
	return tiles
	


if __name__ == "__main__":

	tiles = read_tiles(tiles_fc, tiles_field, tiles_ext)

	tiles_set = set(tiles)
	path = pull_folder

	copied_files = 0
	failed_files = 0

	for (path, dirs, files) in os.walk(path):
		file_set = set(files)  # make it a set
		found_tiles = file_set & tiles_set

		for tile in found_tiles:
			try:
				copy_out(tile, path, output_folder)
				copied_files += 1
				print "copied %s tiles" % copied_files
			except:
				failed_files += 1

	print "Done. %s files successfully copied. %s files failed. Discrepancies mean the tiles were not found" % (copied_files, failed_files)
	stay_open = raw_input("Press any key to close.")
