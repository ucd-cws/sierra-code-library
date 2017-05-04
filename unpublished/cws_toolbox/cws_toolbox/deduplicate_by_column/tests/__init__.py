import unittest
import os

import arcpy

from cws_toolbox import deduplicate_by_column

class DedupeTest(unittest.TestCase):
	def setUp(self):

		self.base_folder = os.path.split(os.path.abspath(__file__))[0]
		self.test_item = os.path.join(self.base_folder, "test_data", "Intersect.gdb", "soil_intersect3")
		self.test_workspace = os.path.join(self.base_folder, "test_data", "testing.gdb")
		self.test_name = arcpy.CreateScratchName(prefix="dedupe_test", workspace=self.test_workspace)

	def test_dedupe(self):
		deduplicate_by_column.deduplicate_by_column(self.test_item, "NHDFlowline_Streams_COMID", "Shape_Length", os.path.join(self.test_workspace, self.test_name))
