import os

run_dir = os.getcwd()

zone_field = "NID"

flag_subprocess_zonal_stats = True # default: False - True means that it will run the zonal stats in a subprocess. Slower, but works around some arcgis issues

bcm_folder = None
usgs_data = "usgs_data"
current_datasets = {"usgs_data":usgs_data}

# sets whether or not to run zonal stats in a subprocess - not implemented
use_subprocesses = True

#temp_gdb = support.check_gdb(run_dir, "temp")

data_folder = os.path.join(run_dir,"data")
input_folder = os.path.join(data_folder,"inputs")
output_folder = os.path.join(run_dir,"output")

input_dataset = os.path.join(input_folder,"dam_catchments","final_dam_catchments.gdb","catchments_minus_bottom_200")

datasets_index = {}
datasets = []

# the following MUST be turned off if the units on the catchment and raster projections are different as it will not account for that.
check_zone_size = False # flag to enable a conservative check on the zone size regarding whether or not any cells will be selected. Right now, when no zones are selected, all of python crashes. problem
