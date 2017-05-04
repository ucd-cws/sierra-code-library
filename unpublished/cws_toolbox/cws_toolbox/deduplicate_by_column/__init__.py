import os

import arcpy

class simple(object):
	"""
		We'll add all the attributes to this on the fly later - can't seem to do it if we just instantiate "object" directly
		Really this functionality should just be provided via a dict since we're not declaring any formal specs here, but
		that's for a future refactoring
	"""
	def __init__(self):
		pass

def index_rows(dataset, filter_column, value_column, OID_field):

	cursor = arcpy.SearchCursor(dataset)

	curs_len = arcpy.GetCount_management(dataset).getOutput(0)

	row_index = {}
	rows = []
	for i in range(int(curs_len)):
		# we're using this method because we wanted everything to stay open and copied, but it probably doesn't work due to cursor structure - it should be switched to for row in cursor

		rows.append(cursor.next())
		
		out_row = simple()  # copy all of the fields to a blank object except the ones we don't care about
		out_row.__dict__[filter_column] = rows[i].getValue(filter_column)
		out_row.__dict__[value_column] = rows[i].getValue(value_column)
		#for field in desc.fields:
		#	try:
		#		out_row.__dict__[field.name] = rows[i].getValue(field.name)
		#	except:
		#		arcpy.AddError("error")
		# store the OID field in a special spot so we can come grab the shape LATER - it's slow, but the only way to do this that I can think of
		# because if we want to index it and retrieve it, the only way to access a particular shape is by reopening it with SQL on the OID field.
		out_row.OIDFieldVal = rows[i].getValue(OID_field)

		key_val = str(rows[i].getValue(filter_column))
		if not row_index.has_key(key_val):
			row_index[key_val] = []
			
		row_index[key_val].append(out_row)
		
		if i % 2000 == 0:
			arcpy.AddMessage(i)

	return cursor, row_index  # keep it alive


def split_features(data, row_index, OID_field, output_dataset, filter_column, value_column, filter_type="filter_max_val"):
	"""
		Creates a 
	:param data: 
	:param row_index: 
	:param OID_field: 
	:param output_dataset: 
	:param filter_column: 
	:param filter_type: 
	:return: 
	"""

	all_features = arcpy.SearchCursor(data)		

	if arcpy.Exists(output_dataset):
		arcpy.Delete_management(output_dataset)
	
	arcpy.Copy_management(data, output_dataset)  #,desc.shapeType,data,"DISABLED","DISABLED",desc.spatialReference)
	upd_curs = arcpy.UpdateCursor(output_dataset)

	filter_func = globals()[filter_type]
	row_ids = []

	arcpy.AddMessage("filtering...")
	for feature in all_features:

		key_value = str(feature.getValue(filter_column))  # wrapped in str because that's how it's indexed
		if key_value not in row_index:  # if we don't have a key for this row anymore, skip it - it was already processed
			arcpy.AddMessage("Dropping a row with duplicate key %s" % key_value)
			continue
		
		real_row = filter_func(row_index[key_value], value_column=value_column) # real_row is the best row that corresponds to this particular row's id

		if real_row is None:
			arcpy.AddMessage("Dropping a row with duplicate key %s" % key_value)
		#	arcpy.AddError("Problem: a value in the filter column returns 0 rows. Should not be possible...")
			continue
	
		row_ids.append(real_row.OIDFieldVal)
		# add key col to array to
		row_index[key_value] = None  # zero it out so we don't use this set of items again
		
	arcpy.AddMessage("writing new features")
	i = 0
	for row in upd_curs:  # delete rows where OID not in array
		i += 1
		if row.getValue(OID_field) not in row_ids:
			upd_curs.deleteRow(row)
			
		if i % 2000 == 0:
			arcpy.AddMessage(i)
		
	del upd_curs  # close the cursor


def filter_max_val(in_list, value_column):
	'''these filters take a list of rows and filter by the column, then spit back out the best row'''
	
	if in_list is None:
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
			max_val = row.__dict__[value_column]
			max_row = row

	return max_row  # it'll be the largest one


def deduplicate_by_column(dataset, filter_column, value_column, output_dataset):
	"""
		Main method of this script
	:return: 
	"""

	desc = arcpy.Describe(dataset)

	if not desc.hasOID:
		arcpy.AddError("The table does not have a unique ID field (OID) field. This tool requires one to proceed")
		return

	OIDField = desc.OIDFieldName

	is_table = False
	if desc.dataType == "Table":
		is_table = True

	arcpy.AddMessage("Indexing rows")
	g_curs, row_index = index_rows(dataset, filter_column, value_column=value_column, OID_field=OIDField)
	arcpy.AddMessage("writing new features")
	split_features(dataset,
								 row_index=row_index,
								 OID_field=OIDField,
								 output_dataset=output_dataset,
								 filter_column=filter_column,
				   				 value_column=value_column,
								)

	return is_table


if __name__ == "__main__":
	input_dataset = arcpy.GetParameterAsText(0)
	output_workspace = arcpy.GetParameterAsText(1)
	output_name = arcpy.GetParameterAsText(2)
	filter_col = arcpy.GetParameterAsText(3)
	value_col = arcpy.GetParameterAsText(4)

	output_dataset = os.path.join(output_workspace, output_name)

	is_table = deduplicate_by_column(input_dataset,
												  filter_column=filter_col,
												  value_column=value_col,
												  output_dataset=output_dataset
												  )

	if not is_table:
		arcpy.MakeFeatureLayer_management(output_dataset, output_name)
		arcpy.SetParameterAsText(6, output_name)
