'''
Created on Aug 28, 2012

@author: nicksantos
'''
import os
import traceback

import arcpy

import code_library
from code_library.common import log
from code_library.common.geospatial import core as geospatial


class Comparison(object):

	def __init__(self):
		self.centroid_distance = None
		self.centroid_direction = None
		self.percent_overlap = None
		self.percent_overlap_initial = None
		self.percent_overlap_final = None
		self.overlap_union_area = None
		self.overlap_intersect_area = None


def get_area(feature_class):
	'''returns the total area of a feature class'''

	temp_fc = geospatial.generate_gdb_filename(return_full=True)
	arcpy.CalculateAreas_stats(feature_class, temp_fc)
	area_field = "F_AREA" # this is hardcoded, but now guaranteed because it is added to a copy and the field is updated if it already exists

	area_curs = arcpy.SearchCursor(temp_fc)
	total_area = 0
	for row in area_curs:
		total_area += row.getValue(area_field)
	del row
	del area_curs

	return total_area


def percent_overlap(feature_one, feature_two, dissolve=False):
	"""
	ArcGIS 10.1 and up. Not for 10.0
	:param feature_one:
	:param feature_two:
	:param dissolve:
	"""

	results = {
		'percent_overlap': None,
		'intersect_area': None,
		'union_area': None,
		'overlap_init_perspective': None,
		'overlap_final_perspective': None,
	}

	if dissolve:
		dissolved_init = geospatial.fast_dissolve(feature_one)
		dissolved_final = geospatial.fast_dissolve(feature_two)
	else:
		dissolved_init = feature_one
		dissolved_final = feature_two

	try:
		log.write("Getting area of Initial...",)
		total_init_area = get_area(dissolved_init)

		log.write("Getting area of Final...",)
		total_final_area = get_area(dissolved_final)
	except:
		log.error("Couldn't get the areas")
		raise

	try:
		log.write("Intersecting...",)
		intersect = geospatial.generate_fast_filename()
		arcpy.Intersect_analysis([dissolved_init, dissolved_final], intersect)

		int_curs = arcpy.da.SearchCursor(intersect, field_names=['SHAPE@AREA', ])
		int_areas = []
		for row in int_curs:
			int_areas.append(row[0])
		intersect_area = sum(int_areas)
		results['intersect_area'] = intersect_area
	except:
		log.error("Couldn't Intersect")
		raise

	try:
		log.write("Unioning...",)
		if len(int_areas) > 0:  # short circuit - if it's 0, we can return 0 as the value
			union = geospatial.generate_fast_filename()
			arcpy.Union_analysis([dissolved_init, dissolved_final], union)
		else:
			return results

		union_curs = arcpy.da.SearchCursor(union, field_names=['SHAPE@AREA'])
		union_areas = []
		for row in union_curs:
			union_areas.append(row[0])
		union_area = sum(union_areas)
		results['union_area'] = union_area
	except:
		log.error("Couldn't Union")
		raise

	log.write("Deleting temporary datasets and Calculating")

	arcpy.Delete_management(intersect)  # clean up - it's an in_memory dataset
	arcpy.Delete_management(union)  # clean up - it's an in_memory dataset

	results['percent_overlap'] = (float(intersect_area) / float(union_area)) * 100
	results['overlap_init_perspective'] = (float(intersect_area) / float(total_init_area)) * 100
	results['overlap_final_perspective'] = (float(intersect_area) / float(total_final_area)) * 100

	return results


def centroid_distance(features=[], spatial_reference=None, max_distance=None, dissolve=False, return_file=False, centroid_direction=False):
	
	'''takes multiple input feature classes, retrieves the centroids of every polygon as points, and writes those points to a file, before running
		PointDistance_analysis() on the data. It returns the out_table given by Point Distance. This is most predictable when two feature classes with a single feature
		are provided. all features must be in the same spatial reference
	'''
	
	if not code_library.isiterable(features):
		raise ValueError("'features' must be an iterable in centroid_distance")
	
	if len(features) == 0:
		raise ValueError("No features to run centroid distance on")
		
	if spatial_reference is None:
		raise ValueError("Spatial Reference cannot be None")
	
	all_centroids = []
	for feature in features:
		try:
			all_centroids += get_centroids(feature, dissolve=dissolve)  # merge, don't append
		except:
			continue  # TODO: Either change this or comment on why it silently continues

	if len(all_centroids) == 0:
		log.warning("No centroids generated - something probably went wrong")
		return False

	point_file = write_features_from_list(all_centroids, "POINT", spatial_reference=spatial_reference)
	log.write("Point File located at %s" % point_file)
	out_table = geospatial.generate_gdb_filename("out_table", return_full=True)
	log.write("Output Table will be located at %s" % out_table)
	
	try:
		arcpy.PointDistance_analysis(point_file, point_file, out_table, max_distance)
	except:
		log.error("Couldn't run PointDistance - %s" % traceback.format_exc())
		return False

	if centroid_direction:
		direction = point_direction(all_centroids, spatial_reference=spatial_reference)
		return {"out_table": out_table, "point_file": point_file, "centroid_direction": direction}  # start just returning a dictionary instead of positional values
	else:
		return {"out_table": out_table, "point_file": point_file, }  # start just returning a dictionary instead of positional values


def point_direction(centroids=None, point1=None, point2=None, spatial_reference=None):
	"""
		Given two points out of a centroid distance calculation, it will run them through Near_analysis and determine the angle, then open
		that result and retrieve the value, returning it. If given more than two points, it will ignore them

		centroids: optional. an interable object containing two geometry objects (as retrieved in centroid_distance). The first one will be used as the primary
		point1: optional. a feature class to use as the primary point.
		point2: optional. a feature class to use as the secondary license. Use either "centroids" or ("point1" and "point2")
		spatial_reference: optional. Used if passing in centroids to write features correctly.
	"""


	if centroids and (point1 or point2):
		raise ValueError("Please define only the centroids or the feature classes, but not both")
	elif not centroids or (point1 and point2):
		raise ValueError("centroids or both point feature classes must be defined")

	if centroids and not spatial_reference:
		raise ValueError("You must set spatial_reference when passing in centroids")

	if centroids:
		point1 = write_features_from_list((centroids[0],), "POINT", spatial_reference=spatial_reference)
		point2 = write_features_from_list((centroids[1],), "POINT", spatial_reference=spatial_reference)

	try:
		arcpy.Near_analysis(point1, point2, angle=True)
		reader = arcpy.da.SearchCursor(point1, field_names=("NEAR_ANGLE",))  # open the input features back up and find the near_angle
		value = reader.next()
		return value[0]  # arcpy.da values are in a tuple with values ordered by the order they're passed in
	except:
		log.error("Unable to get centroid direction")
		return False


def simple_centroid_distance(feature1, feature2, spatial_reference, dissolve=False, return_file=False, centroid_direction=False):
	"""
		wraps centroid_distance and requires that each feature only has 1 polygon in it. Returns the distance value instead of the table. Doesn't check
		whether or not each file has only one polygon, so it will return the FIRST distance value in the out_table, regardless of what it actually is. Don't use this unless you
		are sure you can pass in the correct data
	"""

	if not feature1 or not feature2:
		raise ValueError("feature1 or feature2 is not defined")

	out_attributes = centroid_distance([feature1, feature2], spatial_reference, dissolve=dissolve, return_file=True, centroid_direction=centroid_direction)  # always return file here, but we'll filter it below
	if out_attributes is False:
		return False
	
	reader = arcpy.SearchCursor(out_attributes["out_table"])
	
	distance = None
	i = 0
	for row in reader:
		if i > 1:  # if this is a third iteration of the loop warn the user! The table WILL have two records. One in each direction
			log.warning("Simple Centroid Distance used, but output table has more than two records (the amount for two points). Likely more than two centroids were generated. Check you inputs and use dissolve=True if you aren't already")
			break
		distance = row.getValue("DISTANCE")
		i+=1
		
	del reader

	out_attributes['distance'] = distance
	return out_attributes
	

def write_features_from_list(data=None, data_type="POINT", filename=None, spatial_reference=None, write_ids=False):
	'''takes an iterable of feature OBJECTS and writes them out to a new feature class, returning the filename'''	
	
	if not spatial_reference:
		log.error("No spatial reference to write features out to in write_features_from_list")
		return False
	
	if not data:
		log.error("Input data to write_features_from_list does not exist")
		return False
	
	if not code_library.isiterable(data): # check if exists and that it's Iterable
		log.error("Input data to write_features_from_list is not an Iterable. If you have a single item, pass it in as part of an iterable (tuple or list) please")
	
	filename = geospatial.check_spatial_filename(filename,create_filename = True,allow_fast=False)
	
	if not filename:
		log.error("Error in filename passed to write_features_from_list")
		return False
	
	data_types = ("POINT", "MULTIPOINT", "POLYGON", "POLYLINE")
	if not data_type in data_types:
		log.error("data_type passed into write_features from list is not in data_types")
		return False
	
	path_parts = os.path.split(filename)
	log.write(str(path_parts))
	arcpy.CreateFeatureclass_management(path_parts[0],path_parts[1],data_type,'','','',spatial_reference)

	if write_ids is True:  # if we're supposed to write out the IDs, add a field
		id_field = "feature_id"
		arcpy.AddField_management(filename, id_field, "Long")
	else:
		id_field = False

	valid_datatypes = (arcpy.Point, arcpy.Polygon, arcpy.Polyline, arcpy.Multipoint)
	
	log.write("writing shapes to %s" % filename)
	inserter = arcpy.InsertCursor(filename)
	primary_datatype = None
	
	log.write("writing %s shapes" % len(data))
	#i=0
	for feature in data:
		cont_flag = True # skip this by default if it's not a valid datatype

		if id_field:  # if we're supposed to wirte id_fields, then we have tuples instead, where the first item is the feature, and the second is the ID
			feature_id = feature[1]
			feature_shape = feature[0]
		else:
			feature_shape = feature

		if primary_datatype:
			if isinstance(feature_shape,primary_datatype):
				cont_flag = False
		else:
			for dt in valid_datatypes:
				if isinstance(feature_shape,dt):
					cont_flag = False # check the object against all of the valid datatypes and make sure it's a class instance. If so, set this to false so we don't skip this feature
					primary_datatype = dt # save what the datatype for this file is
		if cont_flag:
			log.warning("Skipping a feature - mixed or unknown datatypes passed to write_features_from_list")
			continue
		try:
			in_feature = inserter.newRow()
			in_feature.shape = feature_shape

			if id_field:  # using this instead of if write_ids since they'll be effectively the same, and the IDE won't complain
				in_feature.setValue(id_field, feature_id)

			#i+=1
			#in_feature.rowid = i
			inserter.insertRow(in_feature)
		except:
			log.error("Couldn't insert a feature into new dataset")
			continue
		
	del feature_shape
	del inserter
	
	return filename


def get_centroids(feature=None, method="FEATURE_TO_POINT", dissolve=False, as_file=False, id_field=False):
	"""
		Given an input polygon, this function returns a list of arcpy.Point objects that represent the centroids

	:param feature: str location of a shapefile or feature class
	:param method: str indicating the method to use to obtain the centroid. Possible values are "FEATURE_TO_POINT"
		(default - more accurate) and "ATTRIBUTE" (faster, but error-prone)
	:param dissolve: boolean flag indicating whether or not to dissolve the input features befor obtaining centroids
	:param as_file: boolean flag indicating whether to return the data as a file instead of a point list
	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field
	:return: list of arcpy.Point objects
	:raise:
	"""
	methods = ("FEATURE_TO_POINT","ATTRIBUTE",) #"MEAN_CENTER","MEDIAN_CENTER")
	
	if not method in methods:
		log.warning("Centroid determination method is not in the set %s" % methods)
		return []
	
	if not feature:
		raise NameError("get_centroids requires a feature as input")
	
	if not check_type(feature,"Polygon"):
		log.warning("Type of feature in get_centroids is not Polygon")
		return []

	if dissolve:  # should we predissolve it?
		t_name = geospatial.generate_fast_filename("dissolved")
		try:
			arcpy.Dissolve_management(feature, t_name, multi_part=True)
			feature = t_name
		except:
			log.warning("Couldn't dissolve features first. Continuing anyway, but the results WILL be different than expected")

	if method == "ATTRIBUTE":
		points = centroid_attribute(feature, id_field=id_field)
		if as_file:
			if (len(points) > 0):
				return_points = write_features_from_list(points,data_type="POINT",filename=None,spatial_reference=feature, write_ids=id_field)  # write_ids = id_field works because it just needs to set it to a non-false value
			else:
				return_points = None

	elif method == "FEATURE_TO_POINT":
		try:
			if as_file:
				return_points = centroid_feature_to_point(feature,as_file=True, id_field=id_field)
			else:
				points = centroid_feature_to_point(feature, id_field=id_field)
		except:
			err_str = traceback.format_exc()
			log.warning("failed to obtain centroids using feature_to_point method. traceback follows:\n %s" % err_str)

	if as_file:
		return return_points
	else:
		return points

def centroid_attribute(feature = None, id_field=False):
	'''for internal use only - gets the centroid using the polygon attribute method - if you want to determine centroids, use get_centroids()


	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field
	'''
	
	curs = arcpy.SearchCursor(feature)
	
	points = []
	for record in curs:
		points.append(record.shape.centroid)
	
	return points

def centroid_feature_to_point(feature,as_file=False, id_field=None):
	"""
	for internal use only

	:param feature: str feature class
	:param as_file: boolean indicates whether to return the arcpy file instead of returning the point array
	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field - can't return ids
	:return: list containing arcpy.Point objects
	"""
	if as_file:
		t_name = geospatial.generate_gdb_filename("feature_to_point") # we don't want a memory file if we are returning the filename
	else:
		t_name = geospatial.generate_fast_filename("feature_to_point")
	
	arcpy.FeatureToPoint_management(feature, t_name,"CENTROID")

	if as_file: #if asfile, return the filename, otherwise, make and return the point_array
		return t_name

	curs = arcpy.SearchCursor(t_name)  # open up the output
	
	points = []
	for record in curs:
		item = None
		shape = record.shape.getPart()

		if id_field:
			shape_id = record.getValue(id_field) # get the shape's point
			item = (shape, shape_id)
		else:
			item = shape

		points.append(item)

	arcpy.Delete_management(t_name)  # clean up the in_memory workspace
	del curs
	
	return points

def get_centroids_as_file(feature=None,filename = None,spatial_reference = None,dissolve=True, id_field=False):
	"""shortcut function to get the centroids as a file - called functions do error checking

	This function used to be more necessary, but is now deprecated by the as_file flag on get_centroids

	:param feature: str file path - required
	:param filename: optional - a filename will be generated
	:param id_field: when included, means to pull ids into a tuple with the centroid from the specified field
	:rtype : str file path location to centroids
	"""
	
	try:
		return get_centroids(feature,dissolve=dissolve,as_file = True, id_field=id_field)
	except:
		err_str = traceback.format_exc()
		log.error("Couldn't get centroids into file - traceback follows:\n %s" % err_str)
	
def check_type(feature = None ,feature_type = None,return_type = False):
	"""

	:param feature:
	:param feature_type:
	:param return_type:
	:return:
	"""


	if not feature:
		log.warning("no features in check_type")
		return False
	
	if not feature_type:
		log.warning("no data_type(s) to check against in ")
		return False
	
	desc = arcpy.Describe(feature)
	
	if desc.dataType == "FeatureClass" or desc.dataType =="FeatureLayer":
		read_feature_type = desc.shapeType
	else:
		log.error("feature parameter supplied to 'check_type' is not a FeatureClass")
		del desc
		return False
	
	del desc
	
	if return_type:
		return read_feature_type
	
	if code_library.isiterable(feature): # if it's an iterable and we have multiple values for the feature_type, then check the whole list
		if read_feature_type in feature_type:
			return True
	elif read_feature_type == feature_type: # if it's a single feature, just check them
		return True	
	
	return False # return False now
	