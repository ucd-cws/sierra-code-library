from __future__ import print_function
import arcpy
import os

# workspace to search for MXDs
workspace = os.path.abspath(os.path.dirname(__file__))

errors = []

def process_directory(directory):

	arcpy.env.workspace = directory
	#print("Searching {0:s} for Map Documents".format(directory))
	# list map documents in folder
	mxdList = arcpy.ListFiles("*.mxd")
	if len(mxdList) > 0:
		print("Found {0} Map Documents in {1:s}".format(len(mxdList), directory))

	# set relative path setting for each MXD in list.
	for map_document in mxdList:
		try:
			filePath = os.path.join(directory, map_document)  # set map document to change
			print("Processing {0:s}".format(map_document))
			mxd = arcpy.mapping.MapDocument(filePath)
			if mxd.relativePaths is True:
				continue
			mxd.relativePaths = True  # set relative paths property
			mxd.save()  # save map document change
		except:  # broad exception - just don't want it to close
			global errors
			errors.append("WARNING: Unable to switch {0:s} to relative paths".format(map_document))
			print("WARNING: Unable to switch {0:s} to relative paths".format(map_document))

for top_path, dirs, files in os.walk(workspace):  # walk the directory tree from here since ListFiles only processes the current directory. Could use these files instead and that'd be cleaner, but this is fine
	for l_dir in dirs:  # for every subdirectory of the current directory
		process_directory(os.path.join(top_path, l_dir))  # process the directory

print("LIST OF ERRORS FOLLOWS - if you don't see any errors, then you're all set")
for error in errors:
	print(error)
	
print("Done processing all documents - hit Enter to close")
		
dont_close_until_confirm = raw_input()
