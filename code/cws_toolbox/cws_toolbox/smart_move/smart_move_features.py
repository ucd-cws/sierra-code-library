__author__ = 'nrsantos'

import os

import arcpy

from code_library.common import log

from . import common

class SmartMoveFeatures(object):
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Smart Move Feature Class"
		self.description = "Moves a Feature Class and searches for references to it in map documents, updating them."
		self.canRunInBackground = True

	def getParameterInfo(self):
		"""Define parameter definitions"""

		features = arcpy.Parameter(
			displayName="Feature Class",
			name="feature_class",
			direction="Input",
			datatype="DEFeatureClass",
            parameterType="Required",
			multiValue=False
		)

		output_location = arcpy.Parameter(
			displayName="Output Location",
			name="output_location",
			direction="Input",
			datatype="DEWorkspace",
            parameterType="Required",
			multiValue=False
		)

		root_folders_to_search = arcpy.Parameter(
			displayName="Root Folders to Search",
			name="root_folders",
			direction="Input",
			datatype="DEFolder",
            parameterType="Required",
			multiValue=True
		)

		exclude_strings = arcpy.Parameter(
			displayName="Exclude Folder if Matches This String",
			name="exclude_folders",
			direction="Input",
			datatype="GPString",
            parameterType="Optional",
			multiValue=True
		)

		params = [features, output_location, root_folders_to_search, exclude_strings]
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

		features = parameters[0].valueAsText
		output_workspace = parameters[1].valueAsText
		root_folders_to_search = parameters[2].valueAsText

		features_name = os.path.splitext(os.path.split(features)[1])[0]
		output_name = os.path.join(output_workspace, features_name)

		common.move_and_update_feature_class(root_folders_to_search, features, output_name)
