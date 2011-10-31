import arcpy, os, traceback

# workspace variables

debug = 1

#predeclaring them so that eclipse doesn't complain
internal_workspace = None
maindb = None
newdb = None
workspace = None
observationsdb = None
layer_cache = None
geo_aux = None

HUCS = None
mxd_source = None
mxd_ddp_source = None
test_folder = None
auto_project = None

all_fish = None
input_rows = None
datasets = None

# Flags set in the arguments that tell it to skip mapping or importing respectively
importonly = 0
maponly = 0
usecache = 0 # skip generating new map layers, use the cache where possible

arc_path = None
projections_path = None
proj_teale_albers = None
proj_utm = None
projections = None # it's ok that it's None now - it will update when the initial variables do.
default_proj = None

def set_workspace_vars(l_workspace = None):
	global internal_workspace, maindb, newdb, workspace, observationsdb, layer_cache, geo_aux
	global HUCS, mxd_source, mxd_ddp_source, test_folder
	global auto_project
	global all_fish, input_rows, datasets
	global arc_path, projections_path, proj_teale_albers, proj_utm, projections, default_proj
	
	if l_workspace == None: # if no l_workspace is provided, then do all this to set the workspace
		os.chdir(os.pardir)
		os.chdir(os.pardir) #ridiculous, but where it's currently at is many layers deep in the directory structure. Need to move to base folder before we getcwd(). Change if code gets moved
		
		internal_workspace = os.getcwd()
		#TODO: Needs to be made a parameter
	else: # set it to what we've provided - this is most likely to occur when called from the test setup function to reset all paths
		os.chdir(l_workspace) # we might not actually want to do this
		internal_workspace = l_workspace
	
	maindb = os.path.join(internal_workspace,"data","fsfish.mdb")
	newdb = os.path.join(internal_workspace,"inputs","new_data.mdb")
	workspace = os.path.join(internal_workspace,"proc","calculations.gdb")
		# TODO: this var may need to be adjusted since so many arc scripts just use it intrinsically for input.
	observationsdb = os.path.join(internal_workspace,"data","observations.gdb")
	layer_cache = os.path.join(internal_workspace,"data","layer_cache.gdb") #TODO: Make argument
	geo_aux = os.path.join(internal_workspace,"data","geo_aux.mdb") #TODO: Make argument
	HUCS = os.path.join(maindb,"HUCs","HUC12FullState")
	
	mxd_source = os.path.join(internal_workspace,"mxds","base","blank.mxd")
	mxd_ddp_source = os.path.join(internal_workspace,"mxds","base","blank_ddp.mxd") # a default to use for USFS layers - probably not particularly useful to have since we're specifiying that doc anyway
	
	test_folder = os.path.join(internal_workspace,"test") #folder where data goes if we are in test mode
	
	#OPTIONS
	auto_project = 1 # sets whether we should attempt to reproject datasets that aren't in Teale Albers. If this is 1, then we will. TODO: Make parameter
	
	# data variables
	all_fish = {}
	input_rows = {} # stores all of the input data by filename for access at the appropriate time - avoids extra SQL connections/releases and can be accessed later
	datasets = []

	# ArcGIS folder
	#arc_path = "%ProgramFiles(X86)%\\ArcGIS\\Desktop10.0"
	arc_path = "C:\\Program Files (x86)\\ArcGIS\\Desktop10.0" # won't work with the environment variable, and nothing in the registry seems to contain the base Arc folder.
	projections_path = os.path.join(arc_path,"Coordinate Systems")
	proj_teale_albers = os.path.join(projections_path,"Projected Coordinate Systems","State Systems","NAD 1983 California (Teale) Albers (Meters).prj")
	proj_utm = os.path.join(projections_path,"Projected Coordinate Systems","UTM","NAD 1983","NAD 1983 UTM Zone 10N.prj")
	projections = {'UTM':proj_utm, 'Teale_Albers':proj_teale_albers}
	default_proj = proj_teale_albers
	
set_workspace_vars() # call it immediately
# import the rest of it AFTER the vars are all defined
import funcs, log, input_filters, observations

# Error Classes

class GenError(Exception):
	def __init__(self, value):
		self.value = value
		log.error(value)
	def __str__(self):
		return repr(self.value)

class IFError(Exception): #an IFError relates to the input filter and determining it. We want to catch it separately
	def __init__(self, value):
		self.value = value
		log.error(str(value))
	def __str__(self):
		return repr(self.value)

class DataProcessingError(Exception):
	def __init__(self, value = None,set_index = None):
		
		if not set_index == None: # if the dataset is provided when the error is raised, remove the dataset from processing
			datasets[set_index] = None #using = None instead of del so that it doesn't get reindexed. We'll need to check for a value when we loop now.
		
		log.error(str(value))
		
		self.value = value # set the error string
	def __str__(self):
		return "\nCritical Error:" + repr(self.value)
	
class DataStorageError(Exception): #used after all the data is processed to detect custom errors
	def __init__(self, value = None):
	
		self.value = value # set the error string
		log.error(value)
	def __str__(self):
		return "\nCritical Error:" + repr(self.value)
	
class MappingError(Exception): #used after all the data is processed to detect custom errors
	def __init__(self, value = None):
	
		self.value = value # set the error string
		
		log.error("%s - stack trace follows: %s" % (value,traceback.print_exc()))
		
	def __str__(self):
		return "\nMapping Error:" + repr(self.value)
	
# Main program classes

class fish: #this class will be used for internal program representation of the fish data table for quick local lookups
	def __init__(self):
		self.species = None
		self.fid = None
		self.alt_codes = []
		
		self.sci_name = None
		#a dictionary of this class will be maintained based on the fid for lookup

class input_data: # used for temporary storage of the db rows
	
	def __init__(self,i1=None,i2=None,i3=None,i4=None,i5=None,i6=None,i7=None,i8=None,i9=None,i10=None,i11=None): # be ready for all of it to be passed in via constructor
		self.ID = i1
		self.Species_ID = i2
		self.Input_Filter = i3
		self.Presence_Type = i4
		self.IF_Method = i5
		self.Observer_ID = i6
		self.Survey_Method = i7
		self.Notes = i8
		self.Source_Data_Notes = i9
		self.Input_Filter_Args = i10
		self.Projection_Key = i11

class observation: #contains data related to a particular observation data file
	def __init__(self):
		self.observer = None
		self.species_fid = None
		self.zone = None # Zone == HUC - trying to make this program a little more generic
		self.obs_date = None
		self.obs_type = None
		self.lat = None # TODO: should this be the polygon centroid for polygons? Same for next
		self.long = None
		self.notes = None # info from the input filter, etc that gets tacked on to the records
		self.other_data = None #place to store additional data from an import that we think is valuable to keep in a human readable form
		self.certainty = None
		self.survey_method = None

class result_set:
	def __init__(self, p_observations = [], p_if_method = None):
		self.observations = p_observations #contains observation objects
		self.if_method = p_if_method

class observation_set: # basic data structure that holds the data we'll be adding to the database
	
	def __init__(self, l_dataset_path = None, l_dataset_name = None): #take it optionally, but allow it to be set later
		self.results = [] #contains result_set objects
		self.species_fid = None
		self.observer = None
		self.obs_date = None
		self.obs_type = None
		self.survey_method = None
		self.dataset_path = l_dataset_path 
		self.dataset_name = l_dataset_name
		self.dataset_key = None # where am I?? Lets it know where it can find itself in the datasets so that it can delete itself 
		self.filter_code = None #the extracted filter defining code from the filename
		self.input_filter = None #the actual, initialized input filter
		self.set_id = None # in the database, that is
		self.new_data = None # the new data object for this item will be moved here
		
		log.write("New observation set constructed - not yet added to the database")
		
		
	def setup(self,dataset_key):

		log.write("Setting up observation set %s" % self.dataset_name)

		self.new_data = input_rows[self.dataset_name]
		del input_rows[self.dataset_name]

		# Set the values to what was brought in with self.new_data
		self.filter_code = self.new_data.Input_Filter
		self.species_fid = self.new_data.Species_ID
		self.observer = self.new_data.Observer_ID
		self.dataset_key = dataset_key
		self.survey_method = self.new_data.Survey_Method
		
#		self.Presence_Type
#		self.IF_Method		
#		self.Survey_Method
#		self.Notes
		
		#Next:
		# Check input filter - make sure it's valid. If it isn't skip the file
		try:
			self.make_input_filter()
			self.check_species()
		except DataProcessingError as error_msg:
			log.write(error_msg,1) # it already should have already removed itself from the list, so long as it was raised with the index value
			return # and stop setting this one up
					
		# TODO: Validate ALL other params. Some can be blank, but if they ARE defined, they need to be valid.
		
		self.new_db_obs_set()
	
	def make_input_filter(self):
		
		#first, check if we have one
		if self.filter_code == None:
			raise DataProcessingError("No input filter set!",self.dataset_key) # if we don't have an input filter, we can stop processing right here
		
		#then make sure it's a valid input filter - could be combined with above, but let's keep it separate for readability
		if not input_filters.IF_List.has_key(self.filter_code):
			raise DataProcessingError("Input filter is invalid. Check the database to make sure it exists - you provided %s" % self.filter_code,self.dataset_key) # if the specified filter doesn't exist, we can stop processing right here
		
		#then, check if we have code for it??
		try:
			l_class = getattr(input_filters, input_filters.IF_List[self.filter_code]) #get the actual class object into l_class
			self.input_filter = l_class(self) # then make a new input filter - the IF_List maps the code to the class - we call it with self as an argument so that it knows where its observation set is
		except:
			raise DataProcessingError("Unable to create input filter object for filter code %s - class should be %s - check to make sure there is a class for the filter code" % (self.filter_code, input_filters.IF_List[self.filter_code]),self.dataset_key)
			
	def check_species(self):
		
		if self.species_fid == "filter":
			#TODO: This should test if the function exists. For tables, we'll need to have determine_species pass back MUL99 (Multiple species - it matches the other format for validation, but is clearly out of the ordinary)
			self.input_filter.determine_species()
		elif all_fish.has_key(self.species_fid):
			pass #we're good! It's already set correctly
		else: #if we've still got nothing, it's either an alt_code or gibberish - if it's not an alt_code, then the following function will throw a DataProcessingError
			self.species_fid = funcs.get_species_from_alt_code(self.species_fid,self.filter_code)
		
		if self.species_fid == "filter" or self.species_fid == None or self.species_fid is False: # the previous attempts failed...
			raise DataProcessingError("Unable to determine the species ID for dataset %s" % self.dataset_name,self.dataset_key)
		
	def process_data(self):
		self.input_filter.process_observations() #dumps results as observations into self.results[]
		# TODO: The following line is a temporary fix - it shouldn't be there and should also do actual processing to determine what should be in place of the "1" - the input filter should retrieve that
		
		#self.add_observations()
		
		#self.import_to_db()
		
		# self.cleanup()
		
	def new_db_obs_set(self):
		
		log.write("Creating new observation set for data")
		
		l_cursor, l_connection = funcs.db_connect(maindb)
		
		try:
			l_query = "insert into Observation_Sets (Species,Input_Filter,Observer,Notes,Dataset_Notes) values (?,?,?,?,?)"
			l_cursor.execute(l_query,self.species_fid,self.filter_code,self.observer,self.new_data.Notes,self.new_data.Source_Data_Notes)
			l_connection.commit()
		except:
			raise DataProcessingError("Unable to add a record to table Observation_Sets for %s. Skipping data - this dataset will be automatically retried next time you run the program")
		
		l_query = "select @@identity as id_value"
		
		l_identity = l_cursor.execute(l_query)
		
		for item in l_identity:
			self.set_id = item.id_value
		log.data_write("Observation Set %s created for %s" % (self.set_id,self.dataset_name))
		
		funcs.db_close(l_cursor,l_connection)
	
	def insert_data(self, db_cursor): # eventually, once all the processing is done, this will add it all to the db
		
		l_sql = "insert into observations (Set_ID,Species_ID,Zone_ID,Presence_Type,IF_Method,Certainty,Longitude,Latitude,Notes,Other_Data,Observation_Date,Survey_Method) values (?,?,?,?,?,?,?,?,?,?,?,?)"
		for result in self.results:
			for obs in result.observations:
				db_cursor.execute(l_sql, self.set_id,obs.species_fid,obs.zone,obs.obs_type,result.if_method.method_id,obs.certainty,obs.long,obs.lat,obs.notes,obs.other_data,obs.obs_date,obs.survey_method)
	
	def record_data(self,db_cursor):
		log.write("Inserting new records for %s" % self.dataset_name, 1)
		log.data_write("Inserting new records for %s" % self.dataset_name)
		self.insert_data(db_cursor) #insert the processed observations into the database
		
		log.write("Copying data source %s to observations database" % self.dataset_name,1)
		self.save_data(db_cursor) # copies the source datafiles to the observations storage database and updates the source locations of the data
	
	def save_data(self,db_cursor): # once we've added the observations, this copies the dataset to the observations database and updates the path in the object and the database
		
		#copy features
		
		new_name = funcs.copy_data(self.dataset_path,observationsdb) #the location defaults to the observations database
			# it returns a new name in case it has to be renamed to be copied
		
		#delete old features from new db
		
		funcs.remove_data(self.dataset_name, newdb)
		if not new_name == None: # if the copy function modified the dataset name
			self.dataset_name = new_name

		#update the database and the object with the new dataset location
		
		self.dataset_path = os.path.join(observationsdb,self.dataset_name)
		l_sql = "update Observation_Sets set Source_Data = ? where Set_ID = ?"
		db_cursor.execute(l_sql,self.dataset_path,self.set_id)

		#mark the input row as imported - we want that info saved in case something went wrong, so don't delete it
		self.cleanup_mark_input_row_imported()
		
		#TODO: Fix import and update code
		
	def	cleanup_mark_input_row_imported(self):
		l_cursor,l_conn = funcs.db_connect(newdb)
		sql_query = "update NewData set Imported = ? where ID = ?"
		l_cursor.execute(sql_query,self.set_id,self.new_data.ID) #TODO change input_rows[...] to the objects path part
			# setting imported = set_id so that we can reimport directly from this record and the stored data in the future
		
		l_conn.commit()
		funcs.db_close(l_cursor,l_conn)


def print_workspace_vars():
	print "\n\nUsing workspace:"
	print "\tMain Database: %s" % maindb
	print "\tInternal Workspace: %s" % internal_workspace
	print "\tWorkspace: %s" % workspace
	print "\tNew Data Database: %s" % newdb
	print "\tObservations Database: %s" % observationsdb
	print "\tLayer Cache: %s" % layer_cache
	print "\tAuxiliary Geographic Data: %s\n" % geo_aux
	
	log.write("Using main database %s,<br/> workspace %s,<br/> new data location %s" % (maindb, arcpy.env.workspace, newdb)) #@UndefinedVariable

def data_setup(): # right now only calls get_species_data(), but in the future could call others without
					#modifying code elsewhere
					
	log.write("Loading Configuration Data",1)
	get_species_data()
	observations.check_observations_db() #checks to make sure we have an observations db to import to
	input_filters.get_IF_list() #populate the IF list
	input_filters.retrieve_if_methods() # populate the listing of methods for each IF
	input_filters.pull_alt_codes()
	observations.get_observation_certainties() # populates the dictionary of default certainties for observations
	pull_field_maps()

def get_species_data():
	
	log.write("Retrieving species data from main database")
	print "Retrieving species data from main database"
	
	db_cursor,db_conn = funcs.db_connect(maindb)
	
	l_sql = 'select FID,Common_Name, Scientific_Name from Species;'
	l_data = db_cursor.execute(l_sql)
	
	for l_item in l_data: # for every fish that's returned from the database
		all_fish[l_item.FID] = fish() #create a new fish object in the all_fish dictionary, keyed on the fid
		all_fish[l_item.FID].fid = l_item.FID #and add the parameter data
		all_fish[l_item.FID].species = l_item.Common_Name
		all_fish[l_item.FID].sci_name = l_item.Scientific_Name
		
	funcs.db_close(db_cursor,db_conn)
	
def pull_field_maps():
	
	db_cursor,db_conn = funcs.db_connect(newdb, "Getting field maps")
	
	l_sql = "select f1.NewData_ID, f1.Field_Name, f1.Input_Field, f1.Handler_Function, f1.Required from FieldMapping as f1 LEFT OUTER JOIN NewData as f2 ON f1.NewData_ID = f2.ID where (f2.Imported = 0 or f1.NewData_ID = 0) order by f1.NewData_ID asc" # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as wellselect f1.NewData_ID, f1.Field_Name, f1.Input_Field, f1.Handler_Function, f1.Required from FieldMapping as f1 OUTER JOIN NewData as f2 ON f1.NewData_ID = f2.ID where f2.Imported = 0 order by f1.NewData_ID asc" # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as wellselect f1.NewData_ID, f1.Field_Name, f1.Input_Field, f1.Handler_Function, f1.Required from FieldMapping as f1 OUTER JOIN NewData as f2 ON f1.NewData_ID = f2.ID where f2.Imported = 0 order by f1.NewData_ID asc" # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as well
	rows = db_cursor.execute(l_sql)
	
	for row in rows:
		if not input_filters.field_maps.has_key(row.NewData_ID): # if we don't already have the array in place
			input_filters.field_maps[row.NewData_ID] = [] # make it into an empty array
			
		l_map = input_filters.field_map()
		l_map.field_name = row.Field_Name
		l_map.handler_function = row.Handler_Function
		l_map.input_field = row.Input_Field
		l_map.set_id = row.NewData_ID
		l_map.required = row.Required
		
		input_filters.field_maps[row.NewData_ID].append(l_map)
		
	funcs.db_close(db_cursor, db_conn)
	
def projection_code_to_file(projection_code): # probably doesn't need to be a function (since it's just looking things up in a dict), but in the interest of a standard interface, this works
	return projections[projection_code]