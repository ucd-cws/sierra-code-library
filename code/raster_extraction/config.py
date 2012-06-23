import os
import sys

import arcpy

import support

run_dir = os.getcwd()

# sets whether or not to run zonal stats in a subprocess
use_subprocesses = True

#temp_gdb = support.check_gdb(run_dir, "temp")

data_folder = os.path.join(run_dir,"data")
input_folder = os.path.join(data_folder,"inputs")
output_folder = os.path.join(run_dir,"output")

input_dataset = os.path.join(input_folder,"gage_catchments_v2.gdb","catchments")

bcm_folder = None
usgs_data = "usgs_data"

current_datasets = {"usgs_issues":"usgs_issues"} # {"usgs_data":usgs_data}
datasets_index = {}
datasets = []

# the following MUST be turned off if the units on the catchment and raster projections are different as it will not account for that.
check_zone_size = False # flag to enable a conservative check on the zone size regarding whether or not any cells will be selected. Right now, when no zones are selected, all of python crashes. problem
zone_field = "SITE_NO"