__author__ = 'nickrsan'

import unittest
import os

import six

from code_library.common import huc_network

test_data = os.path.join(os.path.dirname(__file__), "test_data")


class HUC_Network_Test(unittest.TestCase):

	def setup(self):
		if "setup_run" in self.__dict__:
			return

		self.testhucs_1 = os.path.join(test_data, "eel_river_huc12s.shp")
		self.testhucs_2 = os.path.join(test_data, "eel_river_and_neighbors.shp")

		check = huc_network.setup_network(self.testhucs_2, populate_upstream=True)
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