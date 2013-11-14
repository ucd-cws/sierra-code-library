__author__ = 'nrsantos'

import os

"""
	This library is meant for the same stuff as utils, except for things we want to
	have work without arcpy.
"""

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


def semicolon_split_to_array(value_table): # takes an arcgis value_table (a default for some ArcGIS inputs and parses them to a list)
	# it's possible that there's a better way to do this, depending on how the value_table construct is written.
	return str(value_table).split(';')