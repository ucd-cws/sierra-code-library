import os
import sys

import arcpy

input_dataset = arcpy.GetParameterAsText(0)
output_dataset_folder = arcpy.GetParameterAsText(1)
output_filename = arcpy.GetParameterAsText(2)
filter_column = arcpy.GetParameterAsText(3)
value_column = arcpy.GetParameterAsTest(4)

output_dataset = os.path.join(output_dataset_folder,output_filename)

filter_type = "filter_max_val" # 1 = largest value in column

row_index = {}

def index_rows(dataset,column):
	global row_index
	
	cursor = arcpy.SearchCursor(dataset)
	
	for row in cursor:
		if row_index[str(row.getValue(column))] is None:
			row_index[str(row.getValue(column))] = []
		row_index[str(row.getValue(column))].append(row)

	del cursor
		
def split_features(data):
	'''this could probably be done with an arcgis function - realized after writing...'''
	
	desc = arcpy.Describe(data)

	all_features = arcpy.SearchCursor(data)		
	
	feature_layer = "t_f_layer"
	arcpy.MakeFeatureLayer_management(data,feature_layer) # make it a feature layer so we can use it as a template
	
	arcpy.CreateFeatureclass_management(output_dataset_folder,output_filename,desc.shapeType,feature_layer,"DISABLED","DISABLED",desc.spatialReference)
	ins_curs = arcpy.InsertCursor(output_dataset)
	
	tid = 0
	global row_index
	for feature in features:

		if not row_index.has_key(feature.getValue(filter_column)): # if we don't have a key for this row anymore, skip it - it was already processed
			continue
		else:
			filter_func = globals()[filter_type]
			real_row = filter_func(row_index[feature.getValue(filter_column)]) # real_row is the best row that corresponds to this particular row's id
			
		# copy this point into it
		t_row = ins_curs.newRow()
		for field in desc.fields: # copy each field
			try:
				if field.editable: # only copy the non-system fields
					t_row.setValue(field.name,real_row.getValue(field.name))
			except:
				arcpy.AddWarning("skipping col %s - can't copy" % field.name)
				continue
		
		t_row.shape = real_row.shape # copy the shape over explicitly

		ins_curs.insertRow(t_row)
	
	del ins_curs # close the cursor	
	del desc # kill the describe object
	arcpy.Delete_management(feature_layer) # delete the feature layer
	
def filter_max_val(in_list)
	'''these filters take a list of rows and filter by the column, then spit back out the best row'''
	
	if len(in_list) == 1: # probably a common case - if we only have one item, return that item
		return in_list[0]
	
	max_val = 0
	max_row = None
	for row in in_list:
		if row.getValue(value_column) > max_val:
			max_val = row.getValue(value_column)
			max_row = row
	return row # it'll be the largest one
	
print "indexing rows"
index_rows(input_dataset,filter_column)
print "writing new features"
new_dataset = split_features(input_dataset)

f_layer_name = "deduped_features"
arcpy.MakeFeatureLayer(new_dataset,f_layer_name)

arcpy.SetParameterAsText(5,f_layer_name)