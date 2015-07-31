#-------------------------------------------------------------------------------
# Name:        join tables
# Purpose:     Joins select fields from a whole geodatabase of tables based upon a common key
# Author:      nick santos
#
# Created:     10/24/2011
#-------------------------------------------------------------------------------
# Import system modules
import os, arcpy
import sys
import csv

# Set local variables:
config_join_field = "HUC_12" # the field that it will attempt to join from
config_add_field_names = ["SUM"] # if you want more fields copied over, just do "MEAN","...","..."
config_mega_table = r"" # the location of the table that everything will be joined to
config_input_gdb = ""
config_series = [range(1980,2001),range(2020,2041),range(2050,2071),range(2080,2101)]

config_dbs = ["zonal_tmax_GFDL_A2.gdb",
              #"zonal_stats_tmax.gdb",
              "zonal_run_GFDL_A2.gdb",
              #"zonal_stats_run.gdb",
              "zonal_ppt_GFDL_A2.gdb",
              #"zonal_stats_ppt.gdb",
              "zonal_pck_GFDL_A2.gdb",
              #"zonal_stats_pck.gdb",
              "zonal_tmin_GFDL_A2.gdb",
              #"zonal_stats_tmin.gdb",
              ]

row_index = {}

csv_keys = []
csv_rows = {}
csv_flag = True

def create_unique_table(seed_name):

	global config_input_gdb, config_mega_table, config_add_field_names, config_join_field
	
	uname = arcpy.CreateUniqueName(seed_name,config_mega_table)
	parts = os.path.split(uname)
	arcpy.CreateTable_management(parts[0],parts[1])
	print "Created table %s in file geodatabase\n" % uname
	return os.path.join(config_mega_table,uname)

def check_mega_table_existence(seed_name = "megatable"):

	global config_input_gdb, config_mega_table, config_add_field_names, config_join_field
	
	is_gdb = False
	import re
	if re.search("gdb\/?\\?$", config_mega_table) or re.search("mdb\/?\\?$", config_mega_table): # regex says if the filename ends with gdb or gdb/ or gdb\ - whole line = if it's a file geodatabase
		is_gdb = True
	
	if arcpy.Exists(config_mega_table):
		object_info = arcpy.Describe(config_mega_table)
		if is_gdb: # it's an exiting geodatabase
                        del object_info
        		return create_unique_table(seed_name) # create a table in it
		elif object_info.dataType == "Table":
			del object_info
			return config_mega_table # it's an existing table - just use it
		else: # it's something existing, but we don't know what!
			print "config_mega_table is defined and exists, but is not an arcgis table or an arcgis file geodatabase. Please set it to blank, a table, or a geodatabase"
			sys.exit()
	else: # it doesn't exist
		if is_gdb: # and a gdb path was defined - so create the path
			path_parts = os.path.split(config_mega_table) # get the path and filename
			print "File geodatabase defined, but doesn't exist. Creating"
			arcpy.CreateFileGDB_management(path_parts[0],path_parts[1]) # create it
		elif config_mega_table == "" or config_mega_table is None: # if it's blank
			curdir = os.getcwd() # so we'll create a gdb in the current folder
			gdb_name = "join_table_megatables.gdb"
			gdb_path = os.path.join(curdir,gdb_name)
			if not arcpy.Exists(gdb_path):
				arcpy.CreateFileGDB_management(curdir,gdb_name)
				print "\nCreated file geodatabase to hold mega table in %s" % gdb_path
			config_mega_table = gdb_path # this will be used in the next step
		else: # it's defined, but doesn't exist and we don't know what it is
			print "config_mega_table is defined, but is not an arcgis table or an arcgis file geodatabase. Please set it to blank, a table, or a geodatabase"
			sys.exit()
		
		# now, we have an existing file_gdb again - we can return a table in it
		return create_unique_table(seed_name)		
			
def index_rows(cursor,column,data_column):
	global row_index
	row_index = {} # clear it out
	
	for row in cursor:
		row_index[str(row.getValue(column))] = row.getValue(data_column[0])
	
def fetch_row(key):
	global row_index
	return row_index[key]

def copy_data(from_table,to_table,column_name,use_insert_cursor = False):

	global config_input_gdb, config_mega_table, config_add_field_names, config_join_field, csv_keys, csv_rows

	input_data = arcpy.SearchCursor(from_table)
	if use_insert_cursor is True:
		output_data = arcpy.InsertCursor(to_table)
		for row in input_data:
			new_row = output_data.newRow()
			new_row.setValue(column_name[0],row.getValue(column_name[0]))
			output_data.insertRow(new_row)
                        if csv_flag:
                                join_val = str(row.getValue(column_name[0]))
                                csv_rows[join_val] = {}
        			csv_rows[join_val][column_name[0]] = row.getValue(column_name[0])
	else:
                
		print "Creating cursor"
		output_data = arcpy.UpdateCursor(to_table)
		print "indexing rows"
		index_rows(input_data,config_join_field,column_name) # will make a dictionary for fast lookups of items based on value
		print "Getting data"
		for upd_row in output_data:
                        join_val = str(upd_row.getValue(config_join_field))
                        try:
        			in_row_value = fetch_row(join_val)
        		except: # no row!
                                print "Skipping a row for key value %s" % join_val
                                continue
			upd_row.setValue(column_name[1],in_row_value)
			output_data.updateRow(upd_row)
                        if csv_flag:
                                if not csv_rows.has_key(join_val): # if it doesn't already have rows for it
                                        csv_rows[join_val] = {} # make the dict
                                csv_rows[join_val][column_name[1]] = in_row_value
      			del in_row_value
		
	del output_data
	del input_data
	
def create_columns_from_model(table,columns,model,prefix=None):

	global config_input_gdb, config_mega_table, config_add_field_names, config_join_field, csv_keys
	try:
		model_fields = arcpy.ListFields(model)
	except:
		print "Unable to get information on the join field from the first data table"
		raise
	
	f_names = []

	for field in model_fields:
		if not field.name in columns:
			continue # skip it
		
		if not prefix == None:
			field_name = "%s_%s" % (prefix,field.name)
		else:
			field_name = field.name
			
		f_names.append([field.name,field_name])
			
		try:
			arcpy.AddField_management(table, field_name, field.type) # add a duplicate column in
			csv_keys.append(field_name)
		except:
			print "Unable to add column %s with type %s" % (field.name,field.type)
			raise
	
	return f_names

def write_csv(filename,headers,rows):
        print "Writing csv"
        csvfile = open(filename,'wb')
        csvwriter = csv.DictWriter(csvfile,headers)
        #csvwriter.writeheader() # writeheader is new in 2.7
        headerrow = {}
        for row in headers:
                headerrow[row] = row # make a dict object where the lookup that the dictwriter will use has a value of the header
        csvwriter.writerow(headerrow) # write out the header we just made
        
        for tkey in rows.keys():
                csvwriter.writerow(rows[tkey])

        csvfile.close()
        del csvwriter

for db in config_dbs:

        print "switching databases to %s" % db
        
        config_input_gdb = os.path.join(os.getcwd(),db)


        # Set environment settings
        arcpy.env.workspace = config_input_gdb

        # List tables in mdb
        tables = arcpy.ListTables()

        total_number = len(tables)
        print "%s tables left to process" % total_number
        
        row_index = {}

        for series in config_series:

                print "Switching series to %s" % series[0]
                config_mega_table = r"" # the location of the table that everything will be joined to
                csv_keys = []
                csv_rows = {}
                
                # determine if mega-table is new. If it is, populate it!
                try:
                        seed_name = "%s_%s" %(os.path.splitext(os.path.split(db)[1])[0],series[0])
                        config_mega_table = check_mega_table_existence(seed_name)
                        mega_table_join_field = arcpy.ListFields(config_mega_table,config_join_field)
                except:
                        print "problem loading mega table: ArcGIS error follows"
                        raise

                if len(mega_table_join_field) == 0: # if we don't have the join field
                        print "Creating and populating the join field\n"
                        l_fields = create_columns_from_model(config_mega_table,[config_join_field],tables[0])
                        copy_data(tables[0],config_mega_table,[config_join_field,config_join_field],use_insert_cursor = True)

                for table in tables:
                        print "processing %s" % table

                        if len(series) > 0:
                                filter_found = False
                                for filter_string in series:
                                        if table.find(str(filter_string)) > -1:
                                                filter_found = True
                                if filter_found is False:
                                        print "Filter not found - skipping table"
                                        continue # go to the next table

                        try:
                                l_fields = create_columns_from_model(config_mega_table,config_add_field_names,table, prefix=table) # make the table-prefixed columns
                        except:
                                continue # error message already printed in function
                                
                        for field in l_fields:  # l_fields is the new, prefixed name
                                # field is itself an array with the [unprefixed_name,prefixed_name]
                                try:
                                        copy_data(table,config_mega_table,field)
                                except: # we handle exceptions here because then we can skip the rest of this table
                                        print "Unable to process a row in column %s in table %s - skipping rest of this column table - you should delete those columns and rerun the script for this table (and others with errors) only\n" % (field[0],table)
                                        raise
                                        break
                        
                        total_number = total_number - 1
                        print "completed processing %s - %s remaining\n" % (table,total_number)

                if csv_flag:
                        write_csv(os.path.join(os.getcwd(),"%s.csv" % os.path.split(config_mega_table)[1]),csv_keys,csv_rows)
                
print "\nComplete! As a reminder, the table is located at %s" % config_mega_table
