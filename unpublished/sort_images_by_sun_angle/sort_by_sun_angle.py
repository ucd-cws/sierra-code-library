"""
	Sort by Sun Angle. Sorts images in a folder into two folders (daytime and nightime) based on their sun angle. Requires a latitude and longitude for the images.
	Express latitudes and longitudes in decimal degrees.
	The offset is expressed in degrees of sun angle. Try the default of 0, or if you're trying to capture more dusk time use 5. If you're getting too much darkness, try -5.

	Usage:
	  sort_by_sun_angle.py --lat=<lat> --long=<long> [--offset=<offset>]
"""

__author__ = 'dsx'

import sys
import os
import shutil

import arrow
import Pysolar
import docopt

from code_library.common.mock import Mock

try:
	import arcpy  # if they don't have arcpy, fake it so that code library loads
except:
	sys.modules['arcpy'] = Mock()

from code_library import common  # imported here because we need
from code_library.common.image import remote_cam

arguments = docopt.docopt(__doc__, version="1.x")
if arguments["--lat"] is False or arguments["--long"] is False:
	print __doc__
	sys.exit()
else:
	arguments["--lat"] = float(arguments["--lat"])
	arguments["--long"] = float(arguments["--long"])

if arguments["--offset"] is False or arguments["--offset"] is None:
	print "setting to zero"
	arguments["--offset"] = 0


def is_daytime(sun_angle, daytime_buffer):
	if sun_angle > (0-daytime_buffer):
		return True
	else:
		return False


root_path = os.getcwd()
images = common.utils2.listdir_by_ext(root_path, ".jpg")
night_folder = os.path.join(root_path, "night")
day_folder = os.path.join(root_path, "day")
if not os.path.exists(night_folder):
	os.mkdir(night_folder)
else:
	print "warning, night folder already exists"

if not os.path.exists(day_folder):
	os.mkdir(os.path.join(root_path, "day"))
else:
	print "warning, day folder already exists"

for image in images:
	print image
	img_path = os.path.join(root_path, image)
	image_data = remote_cam.get_remote_cam_image_metadata(img_path)
	img_timestamp = arrow.get(image_data['datetime'] + " -0700", 'MM/DD/YY HH:mm A Z')  # just append the pacific time offset
	sun_angle = Pysolar.GetAltitude(arguments['--lat'], arguments['--long'], img_timestamp.to('utc').datetime)

	if is_daytime(sun_angle, arguments["--offset"]):
		shutil.move(img_path, day_folder)
	else:
		shutil.move(img_path, night_folder)
