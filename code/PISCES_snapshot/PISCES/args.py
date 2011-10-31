import sys, arcpy, os
import vars, log, funcs

args = ['-test','-testdir','-workspace','-maindb','-newdb','-importonly','-maponly','-usecache']

def check_args():
	del sys.argv[0] #strip off the program name from the front
	
	flags = {}
	
	#iterate over the args
	for item in args: #TODO: this is completely innefficient. We already check the args in handle_arg. We essentially check it twice. Fix this sometime when have the chance
		for index, arg in enumerate(sys.argv):
			if item == arg:
				handle_arg(sys.argv[index],sys.argv[index+1],flags)
				del sys.argv[index+1], sys.argv[index] #remove the arguments - don't need to search for them again!
					
	#finally, if there remain args after this, then they didn't use the command line right
	# so we should print a usage note
	
	if flags.has_key("test"):
		funcs.setup_test_mode() #we want this to happen after all of the other args are processed
	
	try: # this is probably a super funky way to do this...
		sys.argv[0]
	except IndexError:
		sys.argv.append(None)
		
	if sys.argv[0] is not None:
		print "Command line usage:\n\tstart.py"
		print "\t\t[-test 1 - sets test mode - makes a copy of data files so we aren't using the real versions"
		print "\t\t[-testdir \"{a folder}\" - sets the location to store the test files. Defaults to a subdir of this program, but setting this can be much faster if working on a network drive."
		print "\t\t[-maindb \"{.mdb location}\"] - location of the main database. This file should be consistent across runs"
		print "\t\t[-workspace \"{.mdb location}\"] - used for scratch work"
		print "\t\t[-newdb \"{.mdb location}\"] - database containing any new information to import"
		
			
def handle_arg(arg,value,flags):
	if(arg == "-workspace"):
		vars.workspace = value
		arcpy.env.workspace = value
		log.write("Workspace set to %s\n" % value,1)
	elif(arg == "-testdir"):
		if value == "temp":
			import tempfile
			vars.test_folder = os.path.join(tempfile.gettempdir(),"fsfish")
		else:
			vars.test_folder = value
		log.write("Test folder set to %s\n" % vars.test_folder,1)
	elif(arg == "-maindb"):
		vars.maindb = value
		log.write("maindb set to %s\n" % value,1)
	elif(arg == "-newdb"):
		vars.newdb = value
		log.write("newdb set to %s\n" % value,1)
	elif(arg == "-maponly"):
		vars.maponly = 1
		vars.importonly = 0
		log.write("Map Only flag set - skipping import\n",1)
	elif(arg == "-importonly"):
		vars.importonly = 1
		vars.maponly = 0
		log.write("Import Only flag set - skipping mapping\n",1)
	elif(arg == "-usecache"):
		vars.usecache = 1
		log.write("Using Layer Cache - This will NOT generate new layers for queries, and any maps that contain queries without existing layers WILL FAIL.\n",1)
	elif(arg == "-test"):
		flags['test'] = 1 # we just set the flag because we want this to happen last