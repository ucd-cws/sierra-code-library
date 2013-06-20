import tempfile
import traceback
import sys
import os

import arcpy

from code_library.common import log
from code_library.common import geospatial

unique_names = {}

def create_unique_name(name,workspace,return_full = False,safe_mode = False):
	"""
	A faster version of arcpy.CreateUniqueName - given a workspace and a name, it returns a unique name

	arcpy.CreateUniqueName starts with the name you give it and iterates until it finds a name that doesn't exist.
	Unfortunately, doing this a few hundred (or thousand) times causes it to slow down the entire program just searching
	for names. Not very useful. So, this version uses arcpy still, but keeps track internally of what number we're on
	so that the search is short (or nonexistent).

	An added bonus of this version is it will return you a full path if you request it with return_full = True. The default
	behavior is just like arcpy though and returns just the new, unique name. Also, a safe_mode flag turns off the extra
	processing for debugging.

	:param name: The base name to make unique
	:param workspace: The workspace it needs to be unique within
	:param return_full: boolean. Whether or not you want the full path returned - defaults to just returning the unique name
	:param safe_mode: # turns off this function's processing and just uses arcpy.CreateUniqueName
	:return:
	"""

	log.write("Generating unique name")

	if not name or not workspace:
		raise ValueError("A name and workspace are required")

	if safe_mode:
		log.write("safe mode - using arc only")
		return arcpy.CreateUniqueName(name, workspace)

	global unique_names
	if name in unique_names:
		unique_names[name] += 1
		return_name = arcpy.CreateUniqueName("%s_%s" % (name, unique_names[name]), workspace)  # generally, this shouldn't be necessary, but if something was created between uses of this function, then this is safer
	else:
		unique_names[name] = 0  # initialize the index
		return_name = arcpy.CreateUniqueName(name) # check the name

	if return_full:
		return os.path.join(workspace, return_name)
	else:
		return return_name


def listdir_by_ext(folder, extension, full=False):
	directory_contents = os.listdir(folder)
	valid_items = []

	if type(extension) == "list" or type(extension) == "tuple":
		# type checking because I don't want to find my code that checks for non-string iterables right now
		for item in directory_contents:
			for ext in extension:
				if _check_ext(item, ext):
					if full:
						valid_items.append(os.path.join(folder, item))
					else:
						valid_items.append(item)
					break  # go to the next item, it won't be more than one ext
	else:
		for item in directory_contents:
			if _check_ext(item, extension):
					if full:
						valid_items.append(os.path.join(folder, item))
					else:
						valid_items.append(item)

	return valid_items


def _check_ext(item, extension):
	ext_len = len(extension)

	if item[-ext_len:].lower() == extension.lower():  # if the extension on the item is the same as our preferred extension
		return True
	else:
		return False