import os

run_dir = os.getcwd()

use_point_estimate = False # warning: If this is set to true, the zone_field should NOT be the primary key (OID) field
							# because it will be changed
zone_field = "NID"

flag_subprocess_zonal_stats = True # default: False - True means that it will run the zonal stats in a subprocess. Slower, but works around some arcgis issues

bcm_folder = None
usgs_issues = "usgs_issues"
usgs_data = "usgs_data"
elev_cm = "elev_extra"
round2 = "round2"
current_datasets = {"round2":round2}

#temp_gdb = support.check_gdb(run_dir, "temp")

data_folder = os.path.join(run_dir,"data")
input_folder = os.path.join(data_folder,"inputs")
output_folder = os.path.join(run_dir,"output")

input_dataset = os.path.join(input_folder,"final_dam_catchments.gdb","dam_catchments_eval_v8_oct")

datasets_index = {}
datasets = []

# the following MUST be turned off if the units on the catchment and raster projections are different as it will not account for that.
check_zone_size = False # flag to enable a conservative check on the zone size regarding whether or not any cells will be selected. Right now, when no zones are selected, all of python crashes. problem
