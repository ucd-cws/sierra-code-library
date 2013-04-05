# Finds all recycle bins and deletes them from the server/machine
# Last update: 3/5/2013

import os
import sys

min_version = (2,6)
if sys.version_info < min_version :
	print "must be run with at least Python 2.6"
	sys.exit(1)
	
#final check before script execution	
raw_input("\nThis script will delete the recycle bin in each logical drive.\nPress Enter to start")
	
	
# puts all logical drive letters in Windows into a list
import string
from ctypes import windll

def get_drives() :
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives
#---end of drive listings---#	


#looks at all of the logical drives
#checks to see if that particular recycle bin exists	
def delete_recyclebin( ) :	
	if __name__ == '__main__':           #list all of the drives.
		drivelist = get_drives()
	else :
		print "There are no drives visible"	
		
	for drive in drivelist :
		#concatenate drive letter and recyclebin to form path
		rpath1=os.path.join(drive + ":\\", rbin1)	
		rpath2=os.path.join(drive + ":\\", rbin2)
		
		#check if the recycle bin exists
		if os.path.exists(rpath1) :
			print "Deleting" , rpath1 , "..."
			os.system(RMCMD + rpath1)
		elif os.path.exists(rpath2) :
			print "Deleting" , rpath2 , "..."
			os.system(RMCMD + rpath2)
		else :
			print "Cannot find recycle bin in drive" , drive , "."
	

rbin1="$Recycle.Bin"   #  7, post2008Server, 2008ServerR2 
rbin2="recycler"	   #  XP, 2003 Server
RMCMD="rd /s /q "       #  delete command on windows

import platform
WIN_VER = platform.release()   #get os version

delete_recyclebin()

raw_input("Press Enter to Exit")













