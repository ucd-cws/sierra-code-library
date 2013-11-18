__author__ = 'nrsantos'

from smart_move.smart_move_features import SamrtMoveFeatures

class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "smart_move"
		self.alias = "Smart Move Operations"

		# List of tool classes associated with this toolbox
		self.tools = [SmartMoveFeatures]