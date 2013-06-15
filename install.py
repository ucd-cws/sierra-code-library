from _winreg import *
import os
from distutils.sysconfig import get_python_lib

curdir = os.getcwd()

print "Registering location in system registry at HKEY_CURRENT_USER\Software\CWS\code_library\location"
print "Registering location as %s" % curdir
try:
	registry = ConnectRegistry("",HKEY_CURRENT_USER)
	Software = OpenKey(registry,"Software")
	CWS = CreateKey(Software,"CWS")
	code_library = CreateKey(CWS,"code_library")
	SetValue(code_library,"location",REG_SZ,curdir)
	FlushKey(code_library)
	print "registered!\n"
except:
	print "FAILED to register"
	
try:
	locations = ("releases\\common\\current","releases\\cws_toolbox\\current","code\\common","code\\cws_toolbox")
	print "Writing location to Python path"
	pth_dir = get_python_lib()
	pth_file = os.path.join(pth_dir,"code_library.pth")
	print "Writing to %s" % pth_file
	open_file = open(pth_file,'w')
	for folder in locations:
		print "Writing %s" % os.path.join(curdir,folder)
		open_file.write(os.path.join(curdir,folder) + "\n")
	open_file.close()
	print "Location written\n"
except:
	print "Couldn't write .pth file to Python install - possibly a permissions issue. Some tools may fail, but the main PISCES software should work"

raw_input("Press Enter to close...")