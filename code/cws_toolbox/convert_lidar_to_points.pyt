from cws_toolbox.convert_lidar_to_points import *

class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "convert_lidar_to_points"
		self.alias = "Test Python Toolbox"

		# List of tool classes associated with this toolbox
		self.tools = [ConvertLidarToPoints]