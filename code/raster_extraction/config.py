import os
import sys

import arcpy

import support

run_dir = os.getcwd()

temp_gdb = support.check_gdb(run_dir, "temp")

data_folder = os.path.join(run_dir,"data")
input_dataset = ""

bcm_folder = None
usgs_data = None

current_datasets = {"usgs_data":usgs_data}
datasets_index = {}
datasets = []

