__author__ = 'nrsantos'

import os

import arcpy

from code_library.common import log

# have a "smart move folder," "smart move geodatabase," "smart move raster," and "smart move feature class." Same underlying code, different move operations
# get the from and to locations
# advanced options for portion of from to match and ways to reference the to. For version 1, it'll be 1:1. Version 2 we can match the from, and version three will allow us to set up how the to is done.

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
			datatype="FeatureClass",
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
			datatype="Folder",
            parameterType="Required",
			multiValue=True
		)

		exclude_strings = arcpy.Parameter(
			displayName="Exclude Folder if Matches This String",
			name="exclude_folders",
			direction="Input",
			datatype="String",
            parameterType="Required",
			multiValue=True
		)

		params = [features, output_location, root_folders_to_search]
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

		move_and_update_feature_class(root_folders_to_search, features, output_name)


def move_and_update_feature_class(folders,original,destination):
	try:
		arcpy.CopyFeatures_management(original,destination)

		if verify(original,destination): # if the verify passes, then delete the original. In theory, we shouldn't get past CopyFeatures without an exception if they aren't the same, but this is arcgis...
			arcpy.Delete_management(original)
	except:
		log.warning("Move operation failed. Exiting")
		return False

	replace_feature_class_locations(folders, original, destination)
	return True


def verify(original, destination):
	if not arcpy.Exists(destination):
		return False

	orig_desc = arcpy.Describe(original)
	dest_desc = arcpy.Describe(destination)

	if orig_desc.extent.equals(dest_desc.extent):
		return True
	else:
		log.warning("Can't verify that copied features are identical - will not delete source.", True)
		return False


def replace_feature_class_locations(folders,original,destination):
	mxds = _find_all_mxds(folders)
	for mxd in mxds:
		_replace_paths_in_mxd(mxd, original, destination)


def _find_all_mxds(folders):
	for folder in folders:
		mxds = []
		arcpy.AddMessage("Finding MXDs in folder %s" % folder)
		mxds += _find_mxds(folder)


def _find_mxds(folder, exclude=(".hg",)):
	"""
		Given a folder, finds all mxds inside of it and subpaths. Recursive
	"""
	mxds = []
	for root, dirs, files in os.walk(folder):

		for filename in files:
			fullpath = os.path.join(root, filename)
			basename, extension = os.path.splitext(fullpath)
			if extension.lower() == ".mxd":
				mxds.append(os.path.join(root, filename))

		for dir in dirs:
			new_path = os.path.join(root,dir)

			skip = False
			for pattern in exclude:
				if pattern in new_path:
					skip = True
			if skip:
				continue

			new_mxds = _find_mxds(new_path)
			if len(new_mxds) > 0:
				mxds += new_mxds

	return mxds


def _replace_paths_in_mxd(mxd_path, original, replacement):

	mxd = arcpy.mapping.MapDocument(mxd_path)
	for lyr in arcpy.mapping.ListLayers(mxd):
		if lyr.supports("DATASOURCE"):
			if lyr.dataSource == original:
				original_replace = os.path.split(original)[0]  # chop off the dataset
				replacement_replace = os.path.split(replacement)[0]
				lyr.findAndReplaceWorkspacePath(original_replace, replacement_replace)
	mxd.save()
	del mxd