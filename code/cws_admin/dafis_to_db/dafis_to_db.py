__author__ = 'nickrsan'

import os
import csv
import pyodbc
import logging
import re
import traceback
import datetime


### CONFIGURATION ###
cfg_debug = False  # When True, prints more data to the log
cfg_cwd = os.getcwd()  # get the directory that we are operating out of
cfg_db_name = "VICEROY.accdb"  # only the database name
cfg_default_db_path = os.path.join(cfg_cwd, cfg_db_name)  # default the path of the database to cfg_db_name in current working directory
cfg_default_input_folder = os.path.join(cfg_cwd, "inputs")  # by default, search for tables in subfolder inputs
cfg_input_file_ext = "txt"  # searches for files only with this extension
cfg_default_table = "tblExistingFundz"  # the name of the primary data table
cfg_default_old_data_table = "tblPriorFundz"  # the name of the table that we'll move old records to

### DAFIS File Specifics
cfg_header_line = 14  # the line in the DAFIS file that contains the header row
cfg_month_and_year_line = 2  # the line with the fiscal period
cfg_month_and_year_regex = '^Fiscal Period:\s+"([^"]+)"\s+\(Year-To-Date\)'  # the regular expression to capture the month and year
cfg_regex_capture_group = 1  # the capture group in the regex that gives us month and year - 0 returns the full line match

cfg_account_line = 4  # the line to parse the account out of - file starts at line 1
cfg_account_regex = '^Account:\s+3-([^\s]+)\s+.*'  # the regular expression to capture the account id
cfg_account_capture_group = 1


cfg_critical_db_keys = ('Account', 'Consolidation', 'Expenditures', 'Encumbrance', 'Balance')
cfg_field_mapping = {  # maps DAFIS fields to our fields - DAFIS fields are the keys for lookup, our fields are the values
	'Account': "Account",
	'Object Consol. Name': "Consolidation",
	'Expenditures': "Expenditures",
	'Encumbrance': "Encumbrance",
	'Balance': "Balance",

	# synonym fields should appear down here to not affect some other (poorly coded) operations
	'Object Consol Name': "Consolidation",  # sometimes appears without a period
	'Consolidation Name': "Consolidation",  # sometimes appears as "Consolidation Name" instead
}

cfg_month_year_field = "last_update"  # field mapped separately because it doesn't come in for each record
cfg_string_keys = ("Account", "Object Consol. Name", "Object Consol Name", "Consolidation Name", )  # all of the keys from the field mapping that need to be inserted as strings (quoted)

cfg_archive_date = "1/1/2012"
cfg_personnel_table = "tblFundingPercentages"
cfg_personnel_old_table = "tblPriorPercentages"


### INIT ###
# don't change the following value unless you know what you're doing. If you set them, the user won't receive a prompt
db_path = None  # default it to None - we'll set if after asking the user
input_folder = None  # default it to None - we'll set if after asking the user
table = None
old_table = None
log = None
archive_date = None

archive_tables = []

class data_file():
	def __init__(self, data=None, month_year=None):
		self.filename = None
		self.data = data
		self.account_raw = None
		self.account = None
		self.month_year_raw = None
		self.month_year = month_year
		self.file_handle = None  # we store the file handle because we'll need to leave it open for a while across funcs


class archive_table():
	"""
		A table that needs to be archived based upon a column value
	"""

	def __init__(self, table_name=None, old_table_name=None, database=None, columns=[]):
		self.table = table_name
		self.old_table = old_table_name
		self.columns = columns
		self.database = database

		self.select = None
		self.delete = None
		self.archive_date = None

	def convert_date(self):
		self.archive_date = datetime.datetime.strptime(self.archive_date, "%m/%d/%Y").date()

	def archive(self):
		"""
			Archives the specified records. Loads all records in the current table, inserts them into the old, then deletes
		"""

		db_cursor, db_conn = db_connect(self.database)
		insert_cursor = db_conn.cursor()

		# get the records, make the insert query, and insert into the selected columns into the old table
		log.debug("Selecting using %s" % self.select)

		records = db_cursor.execute(self.select)
		insert_query = self.make_insert_query()
		for record in records:
			bind_vals = self.order_bind(record)
			log.debug("Inserting using %s" % insert_query)
			insert_cursor.execute(insert_query, *bind_vals)  # expand out the bind_vals into single vals and execute

		# execute the delete query
		log.debug("Deleting using %s" % self.delete)
		db_cursor.execute(self.delete)

		db_conn.commit()
		insert_cursor.close()
		db_close(db_cursor, db_conn)

	def make_insert_query(self):
		query = "insert into %s (" % self.old_table
		second_half = ") values ("
		bind_vals = []

		for item in self.columns:
			query += "%s," % item
			second_half += "?,"

		query = query[:-1]
		second_half = second_half[:-1] # chop the trailing comma off or Access complains
		query += second_half + ")"

		return query

	def order_bind(self, result):
		bind_vals = []
		for column in self.columns:
			try:
				bind_vals.append(result.__getattribute__(column))
			except:
				bind_vals.append("")  # append blank
		return bind_vals


def init():
	log = logging.getLogger(__name__)  # gets a handle for a script specific logger
	if cfg_debug:
		log.setLevel(logging.DEBUG)
	else:
		log.setLevel(logging.INFO)
	FORMAT = "%(asctime)-15s %(message)s"
	logging.basicConfig(format=FORMAT)
	return log


def archive_old(database, l_table, old_table, archive_tables):
	"""
		Takes all existing records in the input table and drops them into the prior data table for history. Then deletes
		the records in the existing table in order to clear the way for the import
	:return:
	"""

	log.info("Archiving Old Data")

	db_cursor, db_conn = db_connect(database)

	copy_records(db_cursor, db_conn, l_table, old_table)  # copy the old records over to the old table
	db_cursor.execute("delete * from %s" % l_table)  # then delete them from the main table
	db_conn.commit()  # the copy inserts new records and the delete removes - save that

	db_close(db_cursor, db_conn)

	for item in archive_tables:
		item.archive()


def copy_records(db_cursor, db_conn, cur_table, old_table):
	log.info("Moving old records")

	# this code is a poor way to do this
	select_string = "select %s as f1, %s as f2, %s as f3, %s as f4, %s as f5, %s as f6 from %s" % (
			cfg_critical_db_keys[0], cfg_critical_db_keys[1], cfg_critical_db_keys[2],
			cfg_critical_db_keys[3], cfg_critical_db_keys[4], cfg_month_year_field, cur_table)
	existing_records = db_cursor.execute(select_string)

	l_cursor = db_conn.cursor()

	insert_string = "insert into %s (%s,%s,%s,%s,%s,%s) values (?,?,?,?,?,?)" % (old_table,
			cfg_critical_db_keys[0], cfg_critical_db_keys[1], cfg_critical_db_keys[2],
			cfg_critical_db_keys[3], cfg_critical_db_keys[4], cfg_month_year_field)

	for record in existing_records:
		l_cursor.execute(insert_string, record.f1, record.f2, record.f3, record.f4, record.f5, record.f6)

	# close the subcursor
	l_cursor.close()


def set_value(item_path=None, default_path=None, name="database", is_path=False):
	"""
	Checks if a path is defined, and if not, gives the user the option to use the default or enter a new one,
	:param item_path: the path to return ultimately. Not defined by default, but users can override it in order to skip prompts
	:param default_path: fully qualified default path
	:param name: Used in prompts to specify the type of file (eg: "DAFIS file" or "database"
	:return: path to use
	"""
	if item_path is None:
		use_default_name = raw_input("Use %s as %s? (y/n):\n" % (default_path, name))
		if use_default_name.lower() == "y" or use_default_name.lower() == "yes":  # if the response in lowercase letters is y or yes
			return default_path  # assign the default
		else:
			prompt_text = "Ok, then what %s should we use?" % name
			if is_path:
				prompt_text += "Please enter a fully qualified path (eg: C:\Users\..)"
			prompt_text += ": "
			return raw_input(prompt_text)
	else:
		return item_path


def get_all_files(folder):
	"""
		gets all of the input files in a folder and adds them as data_file instances to the inputs list. Initializes
		the CSV reader object on it and it appears in the .data attribute of the input items
	:param folder:
	:return:
	"""
	folder_contents = os.listdir(folder)
	inputs = []
	for filename in folder_contents:  # for every file in the folder
		if filename.endswith(cfg_input_file_ext):  # that ends with the specified extension
			try:
				inputs.append(read_data_file(os.path.join(folder, filename)))  # read it into a data_file class object
			except:  # generic exception
				log.error("Couldn't read filename - skipping")

	return inputs


def read_data_file(data_file_path):
	"""
		initializes the file for us and sets up the DictReader
	:param data_file_path:
	:return:
	"""

	results = data_file()  # initialize the storage object
	results.filename = data_file_path
	with open(data_file_path, 'r') as file_handle:  # automatically closes the file on an exception
		lines = file_handle.readlines()
		results.month_year_raw = lines[cfg_month_and_year_line-1]
		results.account_raw = lines[cfg_account_line-1]

	results.month_year = re.search(cfg_month_and_year_regex, results.month_year_raw).group(cfg_regex_capture_group)
	# complicated line - runs the regex on month_year_raw, and takes the capture group IDed in the config and saves it
	results.account = re.search(cfg_account_regex, results.account_raw).group(cfg_account_capture_group)
	log.info("Month and year for file is %s" % results.month_year)
	log.info("Account for file is %s" % results.account)

	file_handle = open(data_file_path, 'rb')  # reopen it for the csv reader
	i = 1  # init on line 1
	while i < cfg_header_line:  # skip a bunch of lines before giving it to the dictreader
		file_handle.next()
		i += 1
	results.file_handle = file_handle  # store the file handle for later to close
	results.data = csv.DictReader(file_handle, delimiter="\t")  # open a DictReader for a tab delimited file

	return results


def db_connect(database):
	database_connection = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+database)
	db_cursor = database_connection.cursor()
	return db_cursor, database_connection


def db_close(curs, conn):
	curs.close()
	conn.close()


def output_all_data(inputs, database_name, table_name):
	"""
		Writes all of the data out to the database, rolling back changes for any files with errors.
	:param inputs: list of input file objects
	:param database_name: the database path to connect to
	:param table_name: the table name to insert records into
	:return:
	"""

	db_cursor, db_conn = db_connect(database_name)

	for dataset in inputs:
		file_failed = False

		log.info("Entering %s" % dataset.filename)

		for row in dataset.data:
			try:
				query = build_query(table_name, row, dataset)
			except ValueError:  # build_query raises ValueError when an empty row is encountered
				continue

			try:
				log.debug("Running query: %s" % query)
				db_cursor.execute(query)
			except:
				error_str = traceback.format_exc(limit=2)
				file_failed = True

		if not file_failed:  # if everything went well for the file
			db_conn.commit()  # commit the entries
		else:  # otherwise, warn the user
			db_conn.rollback()
			log.error("FAILED to insert records for %s. The whole file has been omitted. Error follows: %s" % (dataset.filename, error_str))

		dataset.file_handle.close()  # now that we're done with it, close the file handle

	db_close(db_cursor, db_conn)


def _special_account_case(key, dict_row, query, dataset):
	if key in dict_row and dict_row[key] != "" and dict_row[key] is not None: # if the key exists and isn't empty
		val = dict_row[key]
	else:
		val = dataset.account

	return query + "'%s'," % val


def build_query(table, dict_row, dataset,):
	"""
	Builds a query for a single row. Slower than if we used a single query with placeholders, but guarantees that we
	access the keys in the same order each time and allows for fieldmapping to be a variable placeholder. There is probably
	still a better way to do that (like passing in a list of parameters on query execution), but this is fine for now
	:param table: table to insert into
	:param dict_row: DictReader row object
	:return: sql query
	"""
	query = "insert into %s (" % table

	keys = []
	for key in cfg_field_mapping:  # add the column names
		if key in dict_row:
			keys.append(key)

	if not "Account" in keys:
		keys.append("Account")

	for key in keys:  # need to do this after checking for Account
		query += "%s," % cfg_field_mapping[key]

	if keys[0] in dict_row and dict_row[keys[0]] == "":
		raise ValueError()

	query += "%s) values (" % cfg_month_year_field  # add in the month and year field

	for key in keys:  # add the values
		try:
			if key in cfg_string_keys:  # if the datatype is string for the database, we want to quote the value
				query += "'%s'," % dict_row[key]
			else:  # otherwise, pass it in unquoted
				query += "%s," % dict_row[key]
		except KeyError:  # we have an edge case
			if key == "Account":  # in some cases the account won't exist
				query = _special_account_case(key, dict_row, query, dataset)
			else:
				raise  # if it's not this case, raise the exception

	query += "'%s')" % dataset.month_year  # add in the month and year field value

	return query


log = init()  # initialize variables
if __name__ == '__main__':  # only execute the following code if this is the main executing code - allows us to import, test, and reuse the functions elsewhere

	db_path = set_value(db_path, cfg_default_db_path, "database", is_path=True)  # figure out what the database path is
	input_folder = set_value(input_folder, cfg_default_input_folder, "folder of DAFIS files", is_path=True)
	database_table = set_value(table, cfg_default_table, "database table")
	old_table = set_value(old_table, cfg_default_old_data_table, "old data database table")
	archive_date = set_value(archive_date, cfg_archive_date, "archive date for personnel percentages (<=)")

	# set up the table to archive
	t_tbl = archive_table(cfg_personnel_table, cfg_personnel_old_table, db_path, ["Person", "MoDate", "Account", "Percentage"])
	t_tbl.date_field = "MoDate"
	t_tbl.archive_date = archive_date
	t_tbl.convert_date()
	t_tbl.delete = "delete from %s where %s < CDATE('%s') OR %s = CDATE('%s')" % (t_tbl.table, t_tbl.date_field, t_tbl.archive_date, t_tbl.date_field,  t_tbl.archive_date)
	t_tbl.select = "select * from %s where %s < CDATE('%s') OR %s = CDATE('%s')" % (t_tbl.table, t_tbl.date_field, t_tbl.archive_date, t_tbl.date_field,  t_tbl.archive_date)
	archive_tables.append(t_tbl)

	archive_old(db_path, database_table, old_table, archive_tables)
	log.info("Reading Data Files")
	inputs = get_all_files(input_folder)
	log.info("Writing Outputs To Database")
	output_all_data(inputs, db_path, database_table)
	log.info("Done")

	done = raw_input("Press any key to exit")
