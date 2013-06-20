import csv

from code_library.common import image
from code_library.common import utils


def _extract_baro_from_image(image_name, strip_units):
	if strip_units:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3})\sinHg.*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	else:
		regex = '^\d{0,4}INFORMATION_STRIP_ON__TAG\s+(\d{2}\.\d{1,3}\sinHg).*?(\d{2}\/\d{2}\/\d{2}\s+\d{2}\:\d{2}\s[AP]{1}M)\s+([a-zA-Z0-9]+)'
	capture_group = 1
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

	return image_data


def get_baropressures_from_image_folder(folder, strip_units=True):
	"""
	Gets the baropressures, datetimes, and sites, from all of the remote camera images in a folder, and creates a dict
	for each image with those data. Returns a list containing a dict for each image. image data keys are ('site','datetime','baropressure','filename')
	:param folder: a fully qualified path to a folder containing jpg images with remote-cam baropressures in the EXIF
	:return: list of dicts containing image data
	"""

	files = utils.listdir_by_ext(folder, ".jpg", full=True)  # gets only the jpgs out of the folder
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
	:return: None
	"""

	image_data = get_baropressures_from_image_folder(input_folder, strip_units)

	filehandle = open(output_file, 'wb')
	csv_writer = csv.DictWriter(filehandle, ('id', 'site', 'datetime', 'baropressure', 'filename'))

	if hasattr(csv_writer, "writeheader"):
		csv_writer.writeheader()
	else:
		write_header(csv_writer)

	csv_writer.writerows(image_data)

	filehandle.close()


def write_header(dict_writer):
	header = dict(zip(dict_writer.fieldnames, dict_writer.fieldnames))
	dict_writer.writerow(header)