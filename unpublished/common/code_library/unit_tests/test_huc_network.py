__author__ = 'nickrsan'

import unittest
import os

import six

import arcpy

from code_library.common import huc_network
from code_library import common

test_data = os.path.join(os.path.dirname(__file__), "test_data")
all_hucs = os.path.join(test_data, "ca_huc12s.shp")
huc_10s = r"C:\Users\dsx.AD3\Projects\Scratch\huc_10_validation.gdb\huc_10_w_ds_validated"
test_huc_10s = os.path.join(test_data, "eel_huc_10s.shp")

class HUC_Network_Test(unittest.TestCase):

	def setup(self):
		if "setup_run" in self.__dict__:
			return

		huc_network.pkey_field = "FID"  # fails otherwise with the shapefile ersion

		self.testhucs_1 = os.path.join(test_data, "eel_river_huc12s.shp")
		self.testhucs_2 = os.path.join(test_data, "eel_river_and_neighbors.shp")

		check = huc_network.setup_network(all_hucs, populate_upstream=True)
		if not check:  # error message already printed
			raise ValueError("setup_network failed!")

		self.setup_run = True

	def test_read_hucs(self):
		self.setup()
		huc_ids = huc_network.read_hucs(self.testhucs_1)
		self.assertEqual(len(huc_ids), 113)

	def test_find_outlets(self):
		self.setup()

		huc_ids = huc_network.read_hucs(self.testhucs_1)
		huc_outlets = huc_network.find_outlets(huc_ids)
		self.assertTrue(len(huc_outlets) == 1)  # there should only be one
		self.assertEqual(huc_outlets[0], "180101051102")

	def test_find_multiple_outlets(self):
		self.setup()

		huc_ids = huc_network.read_hucs(self.testhucs_2)
		huc_outlets = huc_network.find_outlets(huc_ids)
		try:
			self.assertTrue(len(huc_outlets) == 3)  # technically 5, but the HUCs are weird
		except AssertionError:
			print "%s huc outlets, expected 5" % len(huc_outlets)
			raise

		self.assertIn("180101070302", huc_outlets)
		self.assertIn("180101070209", huc_outlets)
		self.assertIn("180101070301", huc_outlets)

	def test_find_upstream(self):
		self.setup()
		check = huc_network.setup_network(self.testhucs_2)

		uphucs_1 = huc_network.find_upstream("180101050803", huc_network.watersheds, include_self=True)
		self.assertEqual(3, len(uphucs_1))
		self.assertIn("180101050803", uphucs_1)

		huc_network.short_circuit = False  # now that we've run once, turn off short circuiting so that it runs the rest of these fresh. Probably affects test coverage.
		uphucs_2 = huc_network.find_upstream("180101050803", huc_network.watersheds, include_self=False)
		self.assertEqual(2, len(uphucs_2))
		self.assertNotIn("180101050803", uphucs_2)

		uphucs_3 = huc_network.find_upstream("180101050903", huc_network.watersheds, include_self=True)
		self.assertEqual(6, len(uphucs_3))
		self.assertNotIn("180101050803", uphucs_3)
		self.assertIn("180101050903", uphucs_3)

		uphucs_4 = huc_network.find_upstream("180101050903", huc_network.watersheds, include_self=False)
		self.assertEqual(5, len(uphucs_4))
		self.assertNotIn("180101050903", uphucs_4)
		self.assertNotIn("180101050903", uphucs_4)

	def test_matrix(self, hucs_layer=all_hucs):
		self.setup()

		hucs = huc_network.read_hucs(hucs_layer)
		huc_network.make_upstream_matrix(hucs, os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_outputs"), include_self_flag=True, all_passed=True)

		return os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_outputs", "huc_connectivity_matrix.csv")

	def test_matrix_10(self, hucs_layer=huc_10s):

		huc_network.zones_field = "HUC_10"
		huc_network.ds_field = "HU_10_DS"
		huc_network.pkey_field = "OBJECTID"
		self.setup()

		hucs = huc_network.read_hucs(hucs_layer)
		huc_network.make_upstream_matrix(hucs, os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_outputs"), include_self_flag=True, all_passed=True)

		huc_network.zones_field = "HUC_12"
		huc_network.ds_field = "HU_12_DS"
		huc_network.pkey_field = "FID"

		return os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_outputs", "huc_connectivity_matrix.csv")

	def test_matrix_length(self):
		"""
			Runs the matrix test, then imports the table so we can make assertions about it, such as length, etc
		:return:
		"""
		matrix_file = self.test_matrix(all_hucs)
		huc_length = len(huc_network.read_hucs(all_hucs))

		name, location = common.geospatial.generate_fast_filename(return_full=False)
		arcpy.TableToTable_conversion(matrix_file, location, name)

		table_records = arcpy.GetCount_management(os.path.join(location, name)).getOutput(0)

		## there should be the same number of records as hucs
		self.assertEqual(huc_length, table_records)

		arcpy.Delete_management(os.path.join(location, name))  # free the RAM

	def test_huc_10_contents_and_length(self):

		huc_list = huc_network.read_hucs(test_huc_10s)
		expected_length = len(huc_list)
		huc_list = sorted(huc_list)

		huc_network.zones_field = "HUC_10"
		huc_network.ds_field = "HU_10_DS"

		check = huc_network.setup_network(test_huc_10s, populate_upstream=True)
		if not check:  # error message already printed
			raise ValueError("setup_network failed!")

		upstream = huc_network.find_upstream("1801010511", huc_network.watersheds, False, True)

		self.assertEqual(len(upstream), expected_length)
		self.assertListEqual(huc_list, upstream)

		huc_network.zones_field = "HUC_12"
		huc_network.ds_field = "HU_12_DS"