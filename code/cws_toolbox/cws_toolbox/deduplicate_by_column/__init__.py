import os
import sys

import arcpy

input_dataset = arcpy.GetParameterAsText(0)
output_dataset_folder = arcpy.GetParameterAsText(1)
output_filename = arcpy.GetParameterAsText(2)
filter_column = arcpy.GetParameterAsText(3)
value_column = arcpy.GetParameterAsText(4)

output_dataset = os.path.join(output_dataset_folder,output_filename)

filter_type = "filter_max_val" # filter_max_val = largest value in column

OIDField = None

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
		''' we're using this method because we wanted everything to stay open and copied, but it probably doesn't work due to cursor structure - it should be switched to for row in cursor'''
				
		rows.append(cursor.next())
		
		out_row = simple() # copy all of the fields to a blank object except the ones we don't care about
		out_row.__dict__[filter_column] = rows[i].getValue(filter_column)
		out_row.__dict__[value_column] = rows[i].getValue(value_column)
		#for field in desc.fields:
		#	try:
		#		out_row.__dict__[field.name] = rows[i].getValue(field.name)
		#	except:
		#		arcpy.AddError("error")
		# store the OID field in a special spot so we can come grab the shape LATER - it's slow, but the only way to do this that I can think of
		# because if we want to index it and retrieve it, the only way to access a particular shape is by reopening it with SQL on the OID field.
		out_row.OIDFieldVal = rows[i].getValue(desc.OIDFieldName)
		global OIDField
		OIDField = desc.OIDFieldName
		
		key_val = str(rows[i].getValue(column))
		if not row_index.has_key(key_val):
			row_index[key_val] = []
			
		row_index[key_val].append(out_row)
		
		if i % 500 == 0:
			arcpy.AddMessage(i)
	
	del desc
	return cursor # keep it alive

def split_features(data):
	
	desc = arcpy.Describe(data)

	all_features = arcpy.SearchCursor(data)		
	
	feature_layer = "t_f_layer"
	arcpy.MakeFeatureLayer_management(data,feature_layer) # make it a feature layer so we can use it as a template
	
	if arcpy.Exists(output_dataset):
		arcpy.Delete_management(output_dataset)
	
	arcpy.CopyFeatures_management(feature_layer,os.path.join(output_dataset_folder,output_filename))#,desc.shapeType,data,"DISABLED","DISABLED",desc.spatialReference)
	upd_curs = arcpy.UpdateCursor(output_dataset)
	
	global row_index
	filter_func = globals()[filter_type]

	row_ids = []
	
	arcpy.AddMessage("filtering...")
	for feature in all_features:
		
		if not row_index.has_key(feature.getValue(filter_column)): # if we don't have a key for this row anymore, skip it - it was already processed
			arcpy.AddMessage("Dropping a row with duplicate key %s" % feature.getValue(filter_column))
			continue
		
		real_row = filter_func(row_index[str(feature.getValue(filter_column))]) # real_row is the best row that corresponds to this particular row's id

		if real_row is None:
			arcpy.AddMessage("Dropping a row with duplicate key %s" % feature.getValue(filter_column))
		#	arcpy.AddError("Problem: a value in the filter column returns 0 rows. Should not be possible...")
			continue
	
		row_ids.append(real_row.OIDFieldVal)
		# add key col to array to
		row_index[feature.getValue(filter_column)] = None # zero it out so we don't use this set of items again
		
	arcpy.AddMessage("writing new features")
	i = 0
	for row in upd_curs: # delete rows where OID not in array
		i+= 1
		if row.getValue(OIDField) not in row_ids:
			upd_curs.deleteRow(row)
			
		if i % 500 == 0:
			arcpy.AddMessage(i)
		
	del upd_curs # close the cursor	
	del desc # kill the describe object
	
	arcpy.Delete_management(feature_layer) # delete the feature layer
	
	return output_dataset
	
def filter_max_val(in_list):
	'''these filters take a list of rows and filter by the column, then spit back out the best row'''
	
	#print "%s rows" % len(in_list)
	
	if in_list is None:
		#arcpy.AddMessage("list undefined")
		return None
	
	if len(in_list) == 1: # probably a common case - if we only have one item, return that item
		#print "selected single item"
		print in_list[0].__dict__[value_column]
		return in_list[0]
	
	if len(in_list) == 0:
		#arcpy.AddMessage("Zero-length list")
		return None
	
	max_val = 0
	max_row = None
	
	for row in in_list:
		print row
		if row is None:
			#print "row is None"
			continue
			
		try:
			if not row.__dict__[value_column]:
				#print "row badly indexed"
				continue
		except:
			#print "row badly indexed"
			continue	

		#print "value: %s, max_val: %s" %(row.__dict__[value_column],max_val)
		if row.__dict__[value_column] > max_val:
			#print "it's bigger!"
			
			max_val = row.__dict__[value_column]
			max_row = row
	print max_val
	print max_row
	return max_row # it'll be the largest one
	
arcpy.AddMessage("indexing rows")
g_curs = index_rows(input_dataset,filter_column)
arcpy.AddMessage("writing new features")
new_dataset = split_features(input_dataset)

arcpy.MakeFeatureLayer_management(new_dataset,output_filename)

arcpy.SetParameterAsText(5,output_filename)
