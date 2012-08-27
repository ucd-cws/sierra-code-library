import sqlite3
import tempfile
import os
import datetime

try:
	import arcpy
except:
	pass # it's ok - this won't be run as a script tool if arcpy isn't there

''' Many things in this module would be a little better as class objects with a log class, but then we just end up with a global log object that
	each script would need to load. I think this is cleaner as is, but technically "wrong" '''

log_file = os.path.join(os.getcwd(),"log_db.sqlite3")# this is a default
log_folder = None
print_warnings = True

log_connection = None
log_cursor = None
run_id = None

export_html = True
html_file = None

is_arc_script = False

def init_log(arc_script = False, html = True):
	
	log_folder = os.getcwd() #set a default
	if not os.path.exists(log_file): # try creating it in the default
		log_create(log_file,arc_script)
		log_folder = os.path.split(log_file)[0]
	if not os.path.exists(log_file): # verify that it exists
		log_folder = tempfile.mkdtemp(prefix="code_lib_log")
		global log_file
		log_file = os.path.join(log_folder,"log_db.sqlite3")
		log_create(log_file,arc_script)
	if not os.path.exists(log_file): # verify (again) that it exists
		if arc_script:
			arcpy.AddError("Could not create log file in current or temporary dirs. Can't log")
		else:
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

	global export_html, html_file # set the flag for exporting HTML
	export_html = html
	if export_html:
		html_file = html_setup(log_folder)

	if arc_script:
		global is_arc_script
		is_arc_script = True
	
	write("Log initialized - software loading\nLog DB is located at %s" % log_file)

def write(log_string = None,screen = False, level="log"): # levels are "log", "warning", and "error"
	
	if not log_connection: # if we didn't init manually, create it
		init_log()
		
	global log_cursor, run_id
	if screen is True or (level == "warning" and print_warnings) or level == "error":
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
		if export_html:
			l_date = datetime.datetime.now()
			l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
			html_file.write("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (l_date_string,level,log_string,run_id))
	except:
		if is_arc_script:
			arcpy.AddMessage("Couldn't insert record into log! Printing...")
		else:
			print "Couldn't insert record into log! Printing..."
		if screen is not True and (level != "warning" or print_warnings is False) and level != "error": # in those cases, we already printed it...
			if is_arc_script:
				arcpy.AddMessage(log_string)
			else:
				print log_string

def error(log_string = None,autoprint = True,level="error"): # autoorint is included to prevent crashes from changing log.write to something else in the code. Keeping the signature identical makes our lives easier.
	write(log_string,autoprint,level)

def warning(log_string = None,autoprint = True,level="warning"):
	write(log_string,autoprint,level)

def close_log():
	global log_connection
	global log_cursor
	log_cursor.close()
	log_connection.close()

def log_create(create_log_file,arcpy_based):
	log_connect = sqlite3.connect(create_log_file)
	log_cursor = log_connect.cursor()
	log_cursor.execute('''create table log (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, message_date TEXT, message TEXT, message_level TEXT)''')
	log_cursor.execute('''create table runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT)''')
	log_cursor.close()
	log_connect.close()
	
	if arcpy_based:
		arcpy.AddMessage("Created log file at %s" % create_log_file)
	else:
		print "Created log file at %s" % create_log_file

def html_setup(log_folder):
	filename = os.path.join(log_folder,"log_html.htm")
	
	already_exists = os.path.exists(filename) # store whether it already exists
	
	html_file = open(filename,'a')
	if not already_exists:
		html_file.write("<html><head><title>Log File</title></head><body><table cellspacing = 0 cellpadding=0 cellborder=0><tr><td>Time</td><td>Level</td><td>Message</td><td>Run ID</td>")
	html_file.write("<tr><td colspan=4><h1>New logging instance opened</h1></td></tr>\n")

	return html_file
