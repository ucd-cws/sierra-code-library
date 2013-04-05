# This script checks if any of the local, temp, cookies and arcgis cache folders exists
# If they do exist, then they are deleted for every user on the server. Also, a logfile 
# is created which keeps a record of what has been deleted
#
# Deleted ... usually means that folder has been deleted
# Skipped ... usually means that that folder does not exist
#
# Every log will have a beginning and ending timestamp 
# The number of folders deleted and skipped will be printed at the end.
#
# Last Updated : 3/5/2013


import os
import fnmatch
import socket
import sys

#check user privileges
import ctypes
if (ctypes.windll.shell32.IsUserAnAdmin() != 1 ) :
	print "This script will not run correctly without administrative privileges"

#final check before script execution
raw_input("\nThis script will delete all temporary folders, cookie folders, and arcgis local cache folder of each user.\nPress Enter to start")

#variables
host = socket.gethostname() 
RMCMD="rd /s /q "
userZ="C:\\Users\\"
head="C:\\Documents and Settings\\"
logfilename="pytempclean.log"
logfilepath=os.path.dirname(sys.argv[0]) +"\\" + logfilename
enablelogs = True

cachelist = [
			   "AppData\\Local\\Microsoft\\Windows\\Temporary Internet Files",
			   "AppData\\Local\\Temp",
               "Cookies",
			   "AppData\\Roaming\\ESRI\\Local Caches"
			]

#creates a record of what this script has done.
#log file exists? append to it, otherwise create new one
if(enablelogs) :
	log = open(logfilepath, "ab+")			

#counts folders deleted/skipped
delcount = 0
skipcount = 0	

import time
localtime = time.asctime(time.localtime(time.time()))
if (enablelogs) :
	log.write ("--["+ host +"]---Started-on--- " + localtime + " ------\r\n\r\n")
		
for users in os.listdir(userZ) :
	for folder in cachelist :
		path=head + users + "\\" +folder
		nohead = users + "\\" + folder		#easier to read for logfiles
		if os.path.exists(path) :
			if(enablelogs) :
				log.write ("Deleted " + nohead + "\r\n")
			os.system(RMCMD + path)
			delcount+=1
		else :
			if(enablelogs) :
				log.write ("Skipped " + nohead + "\r\n")
			skipcount+=1

if(enablelogs)	:		
	log.write ("\r\n--["+ host +"]----Ended-on---- " + localtime + " ------\r\n")
	log.write ('%5d' % (delcount));  log.write(" deleted.\r\n" )
	log.write ('%5d' % (skipcount)); log.write(" skipped.\r\n" )
	log.write ('%5d' % (delcount + skipcount)); log.write(" directories total.\r\n\r\n")
	
print '%5d' % delcount," deleted." 
print '%5d' % skipcount, " skipped." 
print '%5d' % (delcount + skipcount), " directories total."

print "Logfile \"",logfilename,"\" is written to", logfilepath	
		
raw_input("\nPress Enter to Exit")
	

	
		