
'''
Created on Jan 23, 2012

@author: nicksantos
'''

import sqlite3

log_connection = None
log_cursor = None
run_id = None

def init_log():
	#log_create()
	log_connect = sqlite3.connect("log_db.sqlite3")
	
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

def write(log_string = None,screen = False, level="log"): # levels are "log", "warning", and "error"
	global log_cursor, run_id
	if screen is True or level == "warning" or level == "error":
		print log_string
	try:
		log_cursor.execute('''insert into log (message,message_date,message_level,run_id) values (?,datetime('now'),?,?)''',(log_string,level,run_id))
	except:
		#print "Couldn't insert record into log! Printing..."
		if screen is not True and level != "warning" and level != "error": # in those cases, we already printed it...
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

def log_create():
	log_connect = sqlite3.connect("log_db.sqlite3")
	log_cursor = log_connect.cursor()
	log_cursor.execute('''create table log (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, message_date TEXT, message TEXT, message_level TEXT)''')
	log_cursor.execute('''create table runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_date TEXT)''')
	log_cursor.close()
	log_connect.close()
