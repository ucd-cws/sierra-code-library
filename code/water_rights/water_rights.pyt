import arcpy
import paramiko

upload_server = r"nicksantos.com"
folder = r"temp/cws"


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "Water Rights Tools"
		self.alias = ""

		# List of tool classes associated with this toolbox
		self.tools = [ViewAvailabilities]


class GenericTool_101(object):

	# following lines are left here as an example. This is really just a template
	#def __init__(self):
	#	"""Define the tool (tool name is the name of the class)."""
		#self.label = "Tool"
		#self.description = ""
		#self.canRunInBackground = False

	def index_params(self, params):
		"""
			Index the parameters so that we can look them up by name rather than position
		"""
		self.params_index = {}
		for param in params:
			self.params_index[param.name] = param

	def getParameterInfo(self):
		"""Define parameter definitions"""
		params = None
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
		return


class ViewAvailabilities(GenericTool_101):
	def __init__(self):
		self.label = "Load and View Availabilities"
		self.description = "Loads the availabilities from the output Excel files for viewing in ArcGIS and basic checking"
		self.canRunInBackground = False

	def getParameterInfo(self):
		model_output_table = arcpy.Parameter(
			displayName="Model Output Sheet in Excel",
			name="model_output_file",
			datatype="DETable",
			parameterType="Required",
			direction="Input")

		symbology_file = arcpy.Parameter(
			displayName="Symbology LayerFile",
			name="symbology_file",
			datatype="DELayer",
			parameterType="Required",
			direction="Input")

		params = [model_output_table, symbology_file]
		self.index_params(params)
		return params

	def execute(self, parameters, messages):

		pass

class SendToWebsite(GenericTool_101):
	def __init__(self):
		self.label = "Approve and Upload Availabilities"
		self.description = "Marks the availabilities as correct and uploads them to the website"
		self.canRunInBackground = False

