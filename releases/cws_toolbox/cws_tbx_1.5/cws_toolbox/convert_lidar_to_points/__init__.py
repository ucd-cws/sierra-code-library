__author__ = 'nrsantos'

#-------------------------------------------------------------------------------
# Name:        LIDAR data to points
# Purpose:
#
# Created:     26/10/2013
# Copyright:   (c) Eric 2013
#-------------------------------------------------------------------------------
import os
import tempfile
import shutil

import arcpy

from code_library.common import geospatial
from code_library.common import utils2


class ConvertLidarToPoints(object):
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Convert Lidar to Points"
		self.description = "Converts batches of CVFED LIDAR data to point files in an output geodatabase"
		self.canRunInBackground = False

	def getParameterInfo(self):
		"""Define parameter definitions"""

		files_to_process = arcpy.Parameter(
			displayName="Files to Process",
			name="files",
			direction="Input",
			datatype="File",
            parameterType="Required",
			multiValue=True
		)

		output_gdb = arcpy.Parameter(
			displayName="Output Geodatabase",
			name="output_geodatabase",
			direction="Input",
			datatype="DEWorkspace",
            parameterType="Required",
		)

		spatial_reference = arcpy.Parameter(
			displayName="Input Spatial Reference",
			name="input_spatial_reference",
			direction="Input",
			datatype="GPSpatialReference",
            parameterType="Required",
		)

		header_row = arcpy.Parameter(
			displayName="Header Row Override",
			name="header_override",
			direction="Input",
			datatype="String",
			parameterType="Optional"
		)

		x = arcpy.Parameter(
			name="x_field",
			displayName="X Coordinate Field",
			direction="Input",
			datatype="Field",
			parameterType="Required",
		)
		y = arcpy.Parameter(
			name="y_field",
			displayName="Y Coordinate Field",
			direction="Input",
			datatype="Field",
			parameterType="Required",
		)
		z = arcpy.Parameter(
			name="z_field",
			displayName="Z Coordinate Field",
			direction="Input",
			datatype="Field",
			parameterType="Optional",
		)

		output_spatial_reference = arcpy.Parameter(
			displayName="Output Spatial Reference",
			name="output_spatial_reference",
			direction="Input",
			datatype="GPSpatialReference",
            parameterType="Required",
		)

		params = [files_to_process, output_gdb, spatial_reference, header_row, x, y, z, output_spatial_reference]
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""
		return

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""

		files_to_process = parameters[0].valueAsText
		output_gdb = parameters[1].valueAsText
		spatial_reference = parameters[2].valueAsText
		header_override = parameters[3].valueAsText
		x = parameters[4].valueAsText
		y = parameters[5].valueAsText
		z = parameters[6].valueAsText
		output_spatial_reference = parameters[7].valueAsText

		files = utils2.semicolon_split_to_array(files_to_process)

		tempdir = tempfile.mkdtemp()

		for table in files:
			arcpy.AddMessage("Processing %s" % table)
			# Set the local variables

			t_out_layer_name_parts = os.path.split(table)
			t_out_layer = os.path.splitext(t_out_layer_name_parts[1])[0]
			original_extension = os.path.splitext(t_out_layer_name_parts[1])[1]
			out_layer = os.path.join(output_gdb, t_out_layer)
			# Set the spatial reference

			using_temp_file = False
			if original_extension.lower() != "csv":
				arcpy.AddMessage("Copying out file")
				using_temp_file = True
				table = self.write_out_to_temp(table, header_override, tempdir)

			# Make the XY event layer...
			arcpy.AddMessage("Making Event Layer (%s,%s)" % (table, t_out_layer))
			arcpy.MakeXYEventLayer_management(table, x, y, t_out_layer, spatial_reference, z)

			# copy it to something that Project can use
			t_dataset = geospatial.generate_gdb_filename(scratch=True)
			arcpy.AddMessage("Loading into RAM (%s)" % t_dataset)
			arcpy.CopyFeatures_management(t_out_layer, t_dataset)
			t_out_layer = t_dataset

			# Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
			# The following inputs are layers or table views: "M395_Compiled_noZeros"
			arcpy.AddMessage("Projecting (%s,%s)" % (t_out_layer, out_layer))
			arcpy.Project_management(t_out_layer, out_layer, output_spatial_reference)

			arcpy.Delete_management(t_dataset)  # kill the in memory copy
			if using_temp_file:
				try:
					os.remove(table)
				except:
					pass  # silently fail - we'll have a final cleanup later

		shutil.rmtree(tempdir)  # cleanup dir in case any deletes failed

	def write_out_to_temp(self, table, header_override, tempdir):

		outfile = os.path.join(tempdir, os.path.splitext(os.path.split(table)[1])[0]) + ".csv"

		if header_override:
			# copy line by line
			input_file = open(table, 'r')
			output_file = open(outfile, 'w')

			output_file.write(header_override)
			for line in input_file:
				output_file.write(line)

			input_file.close()
			output_file.close()

		else:
			shutil.copyfile(table, outfile)
			# copy using a utility

		return outfile





