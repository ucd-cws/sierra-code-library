__author__ = 'nrsantos'

from PIL import Image
from PIL.ExifTags import TAGS
import logging
import re

exif_reg = {}  # a dictionary to hold all of the exif data that was loaded during a program - this way, multiple calls to extract_value_from_exif won't reopen image, etc
log = logging.getLogger("cws_code_library")


def get_exif(image_file=None, exif_registry=None):
	""" Pulls all of the EXIF data from an image and returns it as a dictionary. Base Code Source: http://stackoverflow.com/questions/765396/exif-manipulation-library-for-python
		Enhancements by Nick Santos,  2013
	:param image_file: the fully-qualified path to an image file
	:return: dict
	"""

	if not image_file:
		raise ValueError("Name of image_file must be provided")

	return_dict = {}

	image = Image.open(image_file)
	info = image._getexif()
	for tag, value in info.items():
		decoded = TAGS.get(tag, tag)
		return_dict[decoded] = value

	if exif_registry and type(exif_registry) is dict:
		exif_registry[image_file] = return_dict
	elif exif_registry is not None:
		log.warn("Type of exif_registry must be dict to speed up EXIF retrieval performance. Proceeding without")

	return return_dict


def extract_value_from_exif(filename, tag, regex=None, regex_capture_group=None, exif_registry=None):
	"""
	Extracts a value from an EXIF tag, while speeding up multiple accesses on the same file. Optionally accepts a regex
	and capture group in order to parse out parts of complicated values
	:param filename: the fully qualified filename to process
	:param tag: the EXIF tag to process
	:param regex: (optional) a regular expression that expresses what to return
	:param regex_capture_group: (optional, but required if regex is provided) the id of the capture group in the regular expression that should be used to extract the value
	:param exif_registry: (optional, set automatically) a dictionary to store EXIF data for files in. If not provided, the global one is used.
	:return: string value
	"""

	if not exif_registry:
		global exif_reg
		exif_registry = exif_reg

	if filename in exif_registry:  # if the file has already been processed
		exif_data = exif_registry[filename]  # retrieve the results
	else:
		exif_data = get_exif(filename, exif_registry)  # otherwise, run it for the first time

	if not tag in exif_data:
		log.error("EXIF Tag %s does not exist in this file" % tag)
		return None

	if not regex:
		return exif_data[tag]  # if we don't want to filter the tag data, then just return it
	else:
		if not regex_capture_group:
			raise ValueError("regex_capture_group must be provided if regex is provided. Please provide the capture group number that you wish to extract the value of")
		regex_obj = re.search(regex, exif_data[tag])
		if regex_obj:
			return regex_obj.group(regex_capture_group)
		else:
			log.warn("No data captured by regex")
			return None


