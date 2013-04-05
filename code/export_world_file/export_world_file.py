import os
import sys
import traceback

import arcpy


mxd_name = r'C:\path\to.mxd' # nick, put the path here - leave the r before the quotes
map_resolution = 150 # resolution in pixels
map_width = 1600 # width of the export in pixels
map_height = 1200 # height of the export in pixels
output_folder = os.path.join(os.getcwd(),"output") # where do you want them all put?  defaults to the subfolder output of wherever the script lives

mxd = arcpy.mapping.MapDocument(mxd_name)

if not os.path.exists(output_folder): # if the folder doesn't exist
	os.mkdir(output_folder) # make it

base_name = os.path.splitext(os.path.split(mxd_name)[1])[0] # just the filename part - no path or extension

dataframe = arcpy.mapping.ListDataFrames(mxd)[0]

for pageNum in range(1, mxd.dataDrivenPages.pageCount + 1): #shamelessly taken from esri - loops over every data driven page
	mxd.dataDrivenPages.currentPageID = pageNum # switch pages!
	print "%s..." % pageNum, # print the page number we're on right now
	
	try:
		out_file = os.path.join(output_folder,"%s_%s.jpg" % (base_name,pageNum))
		print out_file
		arcpy.mapping.ExportToJPEG(mxd, out_file, dataframe,map_width,map_height,resolution=map_resolution, world_file=True) # exports the jpeg with the world file
	except: # error handling
		print "Unable to export jpg for %s_%s.jpg" % (base_name,pageNum)
		exc_type, exc_value, exc_traceback = sys.exc_info()
		for item in traceback.format_exception(exc_type, exc_value,exc_traceback):
			print item