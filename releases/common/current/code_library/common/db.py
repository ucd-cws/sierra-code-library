""" Stores common database code for all projects"""

import log

try:
	import pyodbc
except:
	log.warning("Warning: Couldn't load pyodbc. Database calls (relying on code_library.common.db functions will fail). You can safely ignore this warning for many tools")

def db_connect(database):
	database_connection = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+database)
	db_cursor = database_connection.cursor()
	return db_cursor, database_connection


def db_close(curs, conn):
	curs.close()
	conn.close()