import datetime, os
import vars, arcpy

global mylog
global datalog
global errorlog
global arc_script_flag

def write(log_string,auto_print=0):
	print "logs uninitialized" # this will be overridden in init
	
def initialize(log_string = None, arc_script = 0):
	global mylog
	global datalog
	global errorlog
	global arc_script_flag
	global write # we're going to overrride them in order to save log-time processing power - small hit to maintainability
	
	arc_script_flag = arc_script # on init, an arc script will pass this in as "1", which other logging functions will use to determine whether to write an add_message
	
	mylog = open(os.path.join(vars.internal_workspace,"log",'fsfish_processing_log.htm'),'a') # main log file - open the log file in append mode
	datalog = open(os.path.join(vars.internal_workspace,"log",'fsfish_changes.log.txt'),'a') # data log - logs major changes to data between version
	errorlog = open(os.path.join(vars.internal_workspace,"log",'fsfish_error.log.txt'),'a')
	l_date = datetime.datetime.now()
	l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)

	if log_string is not None:
		log_string = " - %s" % log_string
	else:
		log_string = " "
			
	mylog.write("\n<h2>New Run Began at %s%s</h2>\n" % (l_date_string,log_string))
	errorlog.write("\nNew Run Began at %s%s\n" % (l_date_string,log_string))
	
	if arc_script == 0:
		def write(log_string, auto_print=0):
			l_date = datetime.datetime.now()
			l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
		
			mylog.write("<p>%s - %s</p>\n" % (l_date_string,log_string))
			
			if auto_print == 1: # autoprint lets us just make the call to log.write and have it also appear on screen
				print "%s" % log_string
	else:
		def write(log_string, auto_print=0):
			l_date = datetime.datetime.now()
			l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
		
			mylog.write("<p>%s - %s</p>\n" % (l_date_string,log_string))
			
			arcpy.AddMessage("%s" % log_string) # we could theoretically utilize some caller detection to figure out if this is an error (or just have a param) so that we could use AddError instead

def error(log_string):
	l_date = datetime.datetime.now()
	l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
	
	errorlog.write("%s - %s\n" % (l_date_string,log_string))
	write(log_string,1) #autowrite it to the main log and the screen too			
		
def data_write(log_string):
	l_date = datetime.datetime.now()
	l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year,l_date.month,l_date.day,l_date.hour,l_date.minute,l_date.second)
	
	datalog.write("%s - %s\n" % (l_date_string,log_string))
	
def bug(items):
	if type(items) is tuple:
		for item in items:
			print "[%s]" % item
	else:
		print "[%s]" % items