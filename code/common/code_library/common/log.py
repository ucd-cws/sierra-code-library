import sqlite3
import tempfile
import os

try:
	import arcpy
except:
	pass # it's ok - this won't be run as a script tool if arcpy isn't there

log_file = os.path.join(os.getcwd(),"log_db.sqlite3") 

log_connection = None
log_cursor = None
run_id = None

is_arc_script = False

def init_log(arc_script = False):
	
	if not os.path.exists(log_file): # try creating it in the default
		log_create(log_file)
	if not os.path.exists(log_file): # verify that it exists
		tempdir = tempfile.mkdtemp(prefix="code_lib_log")
		global log_file
		log_file = os.path.join(tempdir,"log_db.sqlite3")
		log_create(log_file)
	if not os.path.exists(log_file): # verify (again) that it exists
		print "Could not create log file in current or temporary dirs. Can't log"
		return
	
	log_connect = sqlite3.connect(log_file)
	
	global log_connection
	log_connection = log_connect
	log_connection.isolation_level = None # put the connection into autocommit more
	
	global log_cursor
	log_cursor = log_connect.cursor()
	
	global run_id # set up the run id and the run of the software in the log
	log_cursor.execute('''insert into runs (run_date) values (datetime('now'))''')
	log_cursor.execute('''select last_insert_rowid()''')
	row = log_cursor.fetchone()
	run_id = row[0]

	if arc_script:
		global is_arc_script
		is_arc_script = True
	
	write("Log initialized - software loading\nLog DB is located at %s" % log_file)

def write(log_string = None,screen = False, level="log"): # levels are "log", "warning", and "error"
	
	if not log_connection: # if we didn't init manually, create it
		init_log()
		
	global log_cursor, run_id
	if screen is True or level == "warning" or level == "error":
		if is_arc_script and level == "warning":
			arcpy.AddWarning(log_string)
		elif is_arc_script and level == "error":
			arcpy.AddError(log_string)
		elif is_arc_script:
			arcpy.AddMessage(log_string)
		else:
			print log_string
	try:
		log_cursor.execute('''insert into log (message,message_date,message_level,run_id) values (?,datetime('now'),?,?)''',(log_string,level,run_id))
	except:
		if is_arc_script:
			arcpy.AddMessage("Couldn't insert record into log! Printing...")
		else:
			print "Couldn't insert record into log! Printing..."
		if screen is not True and level != "warning" and level != "error": # in those cases, we already printed it...
			if is_arc_script:
				arcpy.AddMessage(log_string)
			else:
				print log_string

def error(log_string = None,level="error"):
	write(log_string,True,level)

def warning(log_string = None,level="warning"):
	write(log_string,True,level)

def close_log():
	global log_connection
	global log_cursor
	log_cursor.close()
	log_connection.close()

def log_create(create_log_file):
	log_connect = sqlite3.connect(create_log_file)
	log_cursor = log_connect.cursor()
	log_cursor.execute('''create table log (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, message_date TEXT, message TEXT, message_level TEXT)''')
	log_cursor.execute('''create table runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT)''')
	log_cursor.close()
	log_connect.close()
