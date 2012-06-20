import os, sys
import csv
import tempfile

import arcpy

import log

class join_data:
	def __init__(self,db_location,join_field = "HUC_12",add_fields = ["MEAN"],tables = None,dbs = None):
		self.csv_keys = []
		self.csv_rows = {}
		self.csv_flag = True
		
		self.db_location = db_location
		self.join_field = join_field
		self.add_fields = add_fields
		self.tables = tables
		self.dbs = dbs
		
		self.temp_folder = None
		self.temp_gdb = None
		
		if not tables and not dbs:
			raise ValueError("Both tables and dbs are undefined - can't set up join tables with no data")
		
	def create_unique_table(self,seed_name):
	
		uname = arcpy.CreateUniqueName(seed_name,self.mega_table_name)
		parts = os.path.split(uname)
		arcpy.CreateTable_management(parts[0],parts[1])
		print "Created table %s in file geodatabase\n" % uname
		return os.path.join(self.mega_table_name,uname)

	def check_mega_table_existence(self,db_location,seed_name = "megatable"):
			
		is_gdb = False
		import re
		if re.search("gdb\/?\\?$", self.mega_table_name) or re.search("mdb\/?\\?$", self.mega_table_name): # regex says if the filename ends with gdb or gdb/ or gdb\ - whole line = if it's a file geodatabase
			is_gdb = True
		
		if arcpy.Exists(self.mega_table_name):
			object_info = arcpy.Describe(self.mega_table_name)
			if is_gdb: # it's an exiting geodatabase
				del object_info
				return self.create_unique_table(seed_name) # create a table in it
			elif object_info.dataType == "Table":
				del object_info
				return self.mega_table_name # it's an existing table - just use it
			else: # it's something existing, but we don't know what!
				print "config_mega_table is defined and exists, but is not an arcgis table or an arcgis file geodatabase. Please set it to blank, a table, or a geodatabase"
				sys.exit()
		else: # it doesn't exist
			if is_gdb: # and a gdb path was defined - so create the path
				path_parts = os.path.split(self.mega_table_name) # get the path and filename
				print "File geodatabase defined, but doesn't exist. Creating"
				arcpy.CreateFileGDB_management(path_parts[0],path_parts[1]) # create it
			elif self.mega_table_name == "" or self.mega_table_name is None: # if it's blank
				curdir = os.getcwd() # so we'll create a gdb in the current folder
				gdb_name = "join_table_megatables.gdb"
				gdb_path = os.path.join(curdir,gdb_name)
				if not arcpy.Exists(gdb_path):
					arcpy.CreateFileGDB_management(curdir,gdb_name)
					print "\nCreated file geodatabase to hold mega table in %s" % gdb_path
				self.mega_table_name = gdb_path # this will be used in the next step
			else: # it's defined, but doesn't exist and we don't know what it is
				print "config_mega_table is defined, but is not an arcgis table or an arcgis file geodatabase. Please set it to blank, a table, or a geodatabase"
				sys.exit()
			
			# now, we have an existing file_gdb again - we can return a table in it
			return self.create_unique_table(db_location,seed_name)
		
	def index_rows(self,cursor,column,data_column):
		
		self.row_index = {} # clear it out
		
		for row in cursor:
			self.row_index[str(row.getValue(column))] = row.getValue(data_column[0])
		
	def fetch_row(self,key):
		return self.row_index[key]
	
	def copy_data(self,from_table,to_table,column_name,use_insert_cursor = False):
	
		input_data = arcpy.SearchCursor(from_table)
		if use_insert_cursor is True:
			output_data = arcpy.InsertCursor(to_table)
			for row in input_data:
				new_row = output_data.newRow()
				new_row.setValue(column_name[0],row.getValue(column_name[0]))
				output_data.insertRow(new_row)
				if self.csv_flag:
					join_val = str(row.getValue(column_name[0]))
					self.csv_rows[join_val] = {}
					self.csv_rows[join_val][column_name[0]] = row.getValue(column_name[0])
		else:
			
			print "Creating cursor"
			output_data = arcpy.UpdateCursor(to_table)
			print "indexing rows"
			self.index_rows(input_data,self.join_field,column_name) # will make a dictionary for fast lookups of items based on value
			print "Getting data"
			for upd_row in output_data:
				join_val = str(upd_row.getValue(self.join_field))
				try:
					in_row_value = self.fetch_row(join_val)
				except: # no row!
					print "Skipping a row for key value %s" % join_val
					continue
				upd_row.setValue(column_name[1],in_row_value)
				output_data.updateRow(upd_row)
				if self.csv_flag:
					if not self.csv_rows.has_key(join_val): # if it doesn't already have rows for it
						self.csv_rows[join_val] = {} # make the dict
					self.csv_rows[join_val][column_name[1]] = in_row_value
					del in_row_value
			
		del output_data
		del input_data
		
	def create_columns_from_model(self,table,columns,model,prefix=None):
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
				self.csv_keys.append(field_name)
			except:
				print "Unable to add column %s with type %s" % (field.name,field.type)
				raise
		
		return f_names
	
	def write_csv(self,filename,headers,rows):
		log.write("Writing csv",True)
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
		
	def get_tables(self, db):
		# Set environment settings
		arcpy.env.workspace = db
		
		# List tables in db
		tables = arcpy.ListTables()
	
		total_number = len(tables)
		log.write("%s tables left to process" % total_number,True)
		
		return tables	
	
	def pre_merge(self):
		''' if the tables attribute contains a list of lists, then each list contains tables that should be merged again). We'll do that and replace the tables attribute with the merge results
		so that the self.tables attribute contains the kinds of tables we'd expect.'''
		
		try:
			final_tables = []
			for table in self.tables:
				if hasattr(table,"islower"): # essentially, "is it a string?" but done the proper way
					final_tables.append(table)
				else:
					if hasattr(table,"index"): # but it's still a sequence
						final_tables.append(self.merge(table)) # table is a list or other iterable, so we want to merge those items into one
					else:
						raise TypeError("Not a sequence of sequences or a sequence of strings")
			self.tables = final_tables
		except:
			log.error("Incorrect syntax for premerge - likely an incorrect data structure was passed in. It must be either a list (or other iterable) of tables or a list of lists containing tables")
			raise
		
	def merge(self,tables):
		
		merged_data = arcpy.CreateUniqueName("merged",self.get_temp_gdb())		
		return arcpy.Merge_management(tables,merged_data)
		
	def check_temp(self):
		if not self.temp_folder or not self.temp_gdb:
			try:
				self.temp_folder = tempfile.mkdtemp()
				temp_gdb = os.path.join(self.temp_folder,"join_temp.gdb")
				if arcpy.Exists(temp_gdb):
					self.temp_gdb = temp_gdb
				else: # doesn't exist
					log.write("Creating %s" % temp_gdb,True)
					arcpy.CreateFileGDB_management(self.temp_folder,"join_temp.gdb")
					self.temp_gdb = temp_gdb
			except:
				return False
		return True
	
	def get_temp_folder(self):
		if self.check_temp():
			return self.temp_folder
		else:
			raise IOError("Couldn't create temp folder")
	
	def get_temp_gdb(self):
		if self.check_temp():
			return self.temp_gdb
		else:
			raise IOError("Couldn't create temp gdb or folder")

	
		
	def join(self):
		
		# need to check for errors - what if we don't have a db, then what if tables is still empty! # TODO
		if not self.tables:
			self.tables = self.get_tables(db)
		
		self.pre_merge() # checks the tables to ensure that we've got a list that we can actually join
		
		for db in self.dbs:
	
			log.write("switching databases to %s" % db,True)
			
			self.row_index = {}
		
			for series in config_series:
		
				print "Switching series to %s" % series[0]
				config_mega_table = r"" # the location of the table that everything will be joined to
				self.csv_keys = []
				self.csv_rows = {}
				
				# determine if mega-table is new. If it is, populate it!
				try:
					seed_name = "%s_%s" %(os.path.splitext(os.path.split(db)[1])[0],series[0])
					config_mega_table = self.check_mega_table_existence(seed_name)
					mega_table_join_field = arcpy.ListFields(config_mega_table,self.join_field)
				except:
					print "problem loading mega table: ArcGIS error follows"
					raise
		
				if len(mega_table_join_field) == 0: # if we don't have the join field
					print "Creating and populating the join field\n"
					l_fields = self.create_columns_from_model(config_mega_table,[self.join_field],self.tables[0])
					self.copy_data(self.tables[0],config_mega_table,[self.join_field,self.join_field],use_insert_cursor = True)
		
				for table in self.tables:
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
						l_fields = self.create_columns_from_model(config_mega_table,self.add_fields,table, prefix=table) # make the table-prefixed columns
					except:
						continue # error message already printed in function
						
					for field in l_fields:  # l_fields is the new, prefixed name
						# field is itself an array with the [unprefixed_name,prefixed_name]
						try:
							self.copy_data(table,config_mega_table,field)
						except: # we handle exceptions here because then we can skip the rest of this table
							print "Unable to process a row in column %s in table %s - skipping rest of this column table - you should delete those columns and rerun the script for this table (and others with errors) only\n" % (field[0],table)
							raise
							break
					
					total_number = total_number - 1
					print "completed processing %s - %s remaining\n" % (table,total_number)
		
				if self.csv_flag:
					self.write_csv(os.path.join(os.getcwd(),"%s.csv" % os.path.split(config_mega_table)[1]),csv_keys,csv_rows)