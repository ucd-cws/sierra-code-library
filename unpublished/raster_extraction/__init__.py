__author__ = 'nrsantos'

import extract
import config

if __name__ == '__main__':  # used in case of multiprocessing

	extract.extract_data(zones=config.input_dataset, rasters=config.datasets, zone_field=config.zone_field, use_point_estimate=config.use_point_estimate)
