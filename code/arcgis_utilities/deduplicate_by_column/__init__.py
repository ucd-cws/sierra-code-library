import os
import sys

import arcpy

import copy

input_dataset = arcpy.GetParameterAsText(0)
output_dataset_folder = arcpy.GetParameterAsText(1)
output_filename = arcpy.GetParameterAsText(2)
filter_column = arcpy.GetParameterAsText(3)
value_column = arcpy.GetParameterAsText(4)

output_dataset = os.path.join(output_dataset_folder,output_filename)

filter_type = "filter_max_val" # filter_max_val = largest value in column

row_index = {}

arcpy.overwriteOutput = True

class simple():
	def __init__(self):
		pass

def index_rows(dataset,column):
	global row_index

	desc = arcpy.Describe(dataset)
	cursor = arcpy.SearchCursor(dataset)

	curs_len = arcpy.GetCount_management(dataset).getOutput(0)
	
	rows = []
	for i in range(int(curs_len)):
		
		rows.append(cursor.next())
		
		out_row = simple()
		for field in desc.fields:
			if field.editable and (field.name != "Shape") and (field.name != "Shape_Area"):
				#print field.name
				try:
					out_row.__dict__[field.name] = rows[i].getValue(field.name)
				except:
					print "error"
		#print rows[i]
		#print rows[i].shape
		out_row.__dict__['shape'] = copy.copy(rows[i].shape)
		#print "%s,%s,%s,%s" % (rows[i].shape.extent.YMax,rows[i].shape.extent.XMax,rows[i].shape.extent.YMin,rows[i].shape.extent.XMin)
		key_val = str(rows[i].getValue(column))
		if not row_index.has_key(key_val):
			row_index[key_val] = []
			
		row_index[key_val].append(out_row)
		
		if i % 500 == 0:
			print i
		
	return cursor # keep it alive

def split_features(data):
	
	desc = arcpy.Describe(data)

	all_features = arcpy.SearchCursor(data)		
	
	feature_layer = "t_f_layer"
	arcpy.MakeFeatureLayer_management(data,feature_layer) # make it a feature layer so we can use it as a template
	
	if arcpy.Exists(output_dataset):
		arcpy.Delete_management(output_dataset)
	
	arcpy.CreateFeatureclass_management(output_dataset_folder,output_filename,desc.shapeType,data,"DISABLED","DISABLED",desc.spatialReference)
	ins_curs = arcpy.InsertCursor(output_dataset)
	
	tid = 0
	global row_index
	filter_func = globals()[filter_type]
	
	for feature in all_features:

		if not row_index.has_key(feature.getValue(filter_column)): # if we don't have a key for this row anymore, skip it - it was already processed
			continue
		
		real_row = filter_func(row_index[str(feature.getValue(filter_column))]) # real_row is the best row that corresponds to this particular row's id

		if real_row is None:
		#	arcpy.AddError("Problem: a value in the filter column returns 0 rows. Should not be possible...")
			continue
		
		# copy this item into it
		print "[%s],[%s]" % (feature.getValue(filter_column),real_row.__dict__[filter_column])
		
		t_row = ins_curs.newRow()
		for field in desc.fields: # copy each field
			try:
				if field.editable and (field.name != "Shape") and (field.name != "Shape_Area"): # only copy the non-system fields
					t_row.setValue(field.name,real_row.__dict__[field.name])
			except:
				arcpy.AddWarning("skipping col %s - can't copy" % field.name)
				continue
		
		try:
			#print type(real_row.shape)
			print "%s,%s,%s,%s" % (real_row.shape.extent.YMax,real_row.shape.extent.XMax,real_row.shape.extent.YMin,real_row.shape.extent.XMin)
			print real_row.shape
			t_row.shape = real_row.shape # copy the shape over explicitly
		except:
			raise
			print "error copying shape"
		

		ins_curs.insertRow(t_row)
		row_index[feature.getValue(filter_column)] = None # zero it out so we don't use this set of items again
	
	del ins_curs # close the cursor	
	del desc # kill the describe object
	arcpy.Delete_management(feature_layer) # delete the feature layer
	
	return output_dataset
	
def filter_max_val(in_list):
	'''these filters take a list of rows and filter by the column, then spit back out the best row'''
	
	#print "%s rows" % len(in_list)
	
	if in_list is None:
		return None
	
	if len(in_list) == 1: # probably a common case - if we only have one item, return that item
		return in_list[0]
	
	if len(in_list) == 0:
		return None
	
	max_val = 0
	max_row = None
	for row in in_list:
		
		if row is None:
			continue
			
		if row.__dict__[value_column] > max_val:
			#print "[%s][%s]" % (row.getValue(filter_column),row.getValue(value_column))
			max_val = row.__dict__[value_column]
			max_row = row
	return max_row # it'll be the largest one
	
print "indexing rows"
g_curs = index_rows(input_dataset,filter_column)
print "writing new features"
new_dataset = split_features(input_dataset)

f_layer_name = "deduped_features"
arcpy.MakeFeatureLayer_management(new_dataset,f_layer_name)

arcpy.SetParameterAsText(5,f_layer_name)