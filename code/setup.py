from py27distutils.core import setup

setup(name="CWS Toolbox",
	version="1.3.5",
	description="The UCD CWS Code Library and ArcGIS toolbox",
	scripts=['install_code_library.py'],
	packages=['cws_toolbox',
	'cws_toolbox.batch_convert_rasters',
	'cws_toolbox.common',
	'cws_toolbox.deduplicate_by_column',
	'cws_toolbox.join_tables',
	'cws_toolbox.megatable_stats_by_group',
	'cws_toolbox.select_upstream_hucs',
	'cws_toolbox.simple_centroid_distance',
	'cws_toolbox.transform_lidar',
	'code_library',
	'code_library.common',
	'code_library.unit_tests',
	'code_library.common.geospatial',	
	],
	author="Nick Santos, with contributions from other staff",
	author_email="nrsantos@ucdavis.edu",
	url = 'http://bitbucket.org/nickrsan/sierra-code-library',
	package_dir = {'':'.','cws_toolbox':'cws_toolbox/cws_toolbox','code_library':'common/code_library'},
	data_files=[
		('cws_toolbox',['CWS Utilities.tbx','sqlite3.exe']),
	]
)