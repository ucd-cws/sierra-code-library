import os
import sys

import arcpy

import support

run_dir = os.getcwd()

#temp_gdb = support.check_gdb(run_dir, "temp")

data_folder = os.path.join(run_dir,"data")
input_folder = os.path.join(data_folder,"inputs")
output_folder = os.path.join(run_dir,"output")

input_dataset = os.path.join(input_folder,"gage_catchments_v2.gdb","catchments")

bcm_folder = None
usgs_data = "usgs_data"

current_datasets = {"usgs_data":usgs_data}
datasets_index = {}
datasets = []

zone_field = "SITE_NO"