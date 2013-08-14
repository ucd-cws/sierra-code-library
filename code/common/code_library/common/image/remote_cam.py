import csv

from code_library.common import image
from code_library.common import utils2


def _extract_baro_from_image(image_name, strip_units):
	if strip_units:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3})\sinHg.*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	else:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3}\sinHg).*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	capture_group = 1
	tag = "ImageDescription"

	return image.extract_value_from_exif(image_name, tag, regex, capture_group)
	
def _extract_airtemp_from_image(image_name, strip_units):
	if strip_units:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3})\sinHg.+?(\d+).{1}[FC].*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	else:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3})\sinHg.+?(\d+.{1}[FC]).*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	capture_group = 2
	tag = "ImageDescription"

	return image.extract_value_from_exif(image_name, tag, regex, capture_group)

def _extract_datetime_from_image(image_name):
	regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3}\sinHg).*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	capture_group = 2
	tag = "ImageDescription"

	return image.extract_value_from_exif(image_name, tag, regex, capture_group)


def _extract_site_from_image(image_name):
	regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3}\sinHg).*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	capture_group = 3
	tag = "ImageDescription"

	return image.extract_value_from_exif(image_name, tag, regex, capture_group)


def get_remote_cam_image_metadata(image_name, strip_units=True):
	image_data = {}
	image_data['site'] = _extract_site_from_image(image_name)
	image_data['datetime'] = _extract_datetime_from_image(image_name)
	image_data['baropressure'] = _extract_baro_from_image(image_name, strip_units)
	image_data['filename'] = image_name
	image_data['airtemp'] = _extract_airtemp_from_image(image_name,strip_units)

	return image_data


def get_baropressures_from_image_folder(folder, strip_units=True):
	"""
	Gets the baropressures, datetimes, and sites, from all of the remote camera images in a folder, and creates a dict
	for each image with those data. Returns a list containing a dict for each image. image data keys are ('site','datetime','baropressure','filename')
	:param folder: a fully qualified path to a folder containing jpg images with remote-cam baropressures in the EXIF
	:return: list of dicts containing image data
	"""

	files = utils2.listdir_by_ext(folder, ".jpg", full=True)  # gets only the jpgs out of the folder
	image_records = []

	i = 1
	for image in files:
		image_data = get_remote_cam_image_metadata(image, strip_units)
		image_data['id'] = i
		image_records.append(image_data)
		i += 1

	return image_records


def baropressures_to_file(input_folder, output_file, strip_units=True):
	"""
	Obtains metadata for all of the remote camera images in an input folder, and writes it out to a csv
	:param input_folder: str The folder to get the images from
	:param output_file: str The file to write out to
	:param strip_units: boolean Whether or not to include units in the data elements that contain them. If True, units will removed from output. If False, they will be included. Default: True
	:return: None
	"""
	
	image_data = get_baropressures_from_image_folder(input_folder, strip_units)

	filehandle = open(output_file, 'wb')
	keys = image_data[0].keys()
	keys.reverse()	# doing this as an intermediate because image_data[0].keys().reverse() returns nothing, and instead modifies in place.
	csv_writer = csv.DictWriter(filehandle, keys) # passing in image_data[0].keys() just tells it what the fields to look for. reversing it because usually it comes out last to first

	if hasattr(csv_writer, "writeheader"): # if we're running a version of Python >= 2.7, then this is built in. Use it
		csv_writer.writeheader()
	else:
		write_header(csv_writer) # if not, use our own implementation below

	csv_writer.writerows(image_data)

	filehandle.close()


def write_header(dict_writer):
	header = dict(zip(dict_writer.fieldnames, dict_writer.fieldnames))
	dict_writer.writerow(header)