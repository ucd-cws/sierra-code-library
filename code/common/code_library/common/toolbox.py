__author__ = 'dsx'

def index_params(tool, params):
	"""
		Indexes parameters to ArcGIS Python script tools so that they can be looked up by name. May not work for getting data, but
		should at least allow reading of info.
	"""
	tool.params_index = {}
	for param in params:
		tool.params_index[param.name] = param
