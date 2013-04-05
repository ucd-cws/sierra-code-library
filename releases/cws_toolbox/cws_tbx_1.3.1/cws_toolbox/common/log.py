
'''
Created on Jan 23, 2012
Updated 2/6/2012

@author: nicksantos
'''

import os
import sqlite3

import arcpy

log_connection = None
log_cursor = None
run_id = None

arc_script = False

def init_log(arcgis_s = False):	
	db_name = get_db_name(os.environ['USERNAME']) # this function returns the name for the specific user - this way they are all writing to different sqlite logs in case they are running at the same time.
	
	log_connect = sqlite3.connect(db_name)
	
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
	
	write("Log initialized - software loading")
	
	if arcgis_s is True: # if this has been initialized from an arcgis script tool
		global arc_script
		arc_script = True
		write("Logging mode set to arcgis script tool - output will be ")

def write(log_string = None, level="log"): # levels are "log", "warning", "debug", and "error"
	global log_cursor, run_id

	log_cursor.execute('''insert into log (message,message_date,message_level,run_id) values (?,datetime('now'),?,?)''',(log_string,level,run_id))
	
	if level == "warning":
		log_string = "Warning: %s" % log_string
	elif level == "error":
		log_string = "ERROR: %s" % log_string
	
	if arc_script is False:
		if not (level == "debug" or level == "store"): # we don't print debug info
			print log_string
	else:
		if level == "warning":
			arcpy.AddWarning(log_string)
		elif level == "error":
			arcpy.AddError(log_string)
		elif not (level == "debug"):
			arcpy.AddMessage(log_string)

def close_log():
	global log_connection
	global log_cursor
	log_cursor.close()
	log_connection.close()

def get_db_name(username):
	
	log_db_name = "tools_log_%s.sqlite3" % username
	
	if not os.path.exists(os.path.join(os.getcwd(),log_db_name)):
		log_create(log_db_name)
		
	return log_db_name
		
def log_create(filename):
	log_connect = sqlite3.connect(filename)
	log_cursor = log_connect.cursor()
	log_cursor.execute('''create table log (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, message_date TEXT, message TEXT, message_level TEXT)''')
	log_cursor.execute('''create table runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT)''')
	log_cursor.close()
	log_connect.close()