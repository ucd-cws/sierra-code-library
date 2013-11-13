""" Stores common database code for all projects"""

import pyodbc

def db_connect(database):
	database_connection = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+database)
	db_cursor = database_connection.cursor()
	return db_cursor, database_connection


def db_close(curs, conn):
	curs.close()
	conn.close()