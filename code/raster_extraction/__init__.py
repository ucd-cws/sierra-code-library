import os
import sys

import arcpy

import join_tables
import zonal_stats
import support 
import log
import config

support.setup(config.input_dataset)
support.run_files([config.input_dataset],config.datasets)


