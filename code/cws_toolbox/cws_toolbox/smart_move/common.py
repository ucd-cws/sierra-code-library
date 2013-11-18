__author__ = 'nrsantos'

import os

import arcpy

from code_library.common import log


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