import os
import sys

import arcpy

import join_tables
import zonal_stats
import support 
import log
import config

if __name__ == '__main__': # used in case of multiprocessing
	support.setup(config.input_dataset)
	support.run_files([config.input_dataset],config.datasets)


