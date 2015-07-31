import os
import sys
import re

import arcpy

from code_library.common.math import min_max 
mm = min_max()

wdir = None
input_dir = None
output_dir = None
all_files = []
log_file = None

def setup(out_d = None):

	global wdir, input_dir,output_dir,log_file, all_files

	output_dir = out_d
	all_files = [arcpy.GetParameterAsText(0)]
	
	try:
		wdir = os.getcwd()
		if len(all_files) == 0:
			input_dir = os.path.join(wdir,"input_files")
			all_files = load_files_from_folder(input_dir)
		else:
			input_dir = os.path.split(all_files[0])[0] # get the path of the first item in the all_files list
		
		if (output_dir is None or output_dir == "") and out_d is not None:
			output_dir = os.path.join(wdir,"output_files")
			if not os.path.exists():
				os.makedirs(output_dir)
	except:
		print "Couldn't set up working directories"
		sys.exit()

	try:
		log_file = open(os.path.join(wdir,"log.txt"),'w')
	except:
		print "Couldn't set up log"
		sys.exit()
	
	
	log("Output_dir = %s" % output_dir)
	
def log(statement):
	arcpy.AddMessage(statement)
	log_file.write("%s" % statement)


def load_files_from_folder(load_folder):
	try:
		all_files = os.listdir(load_folder)
	except:
		log("Couldn't get contents of input directory")
	
	for i in range(len(all_files)): # prepend the path
		all_files[i] = os.path.join(load_folder,all_files[i])		
	
	return all_files

def process_data(process_instance):
	for cur_file in all_files:
		try:
			log("Processing file %s" % cur_file)
			data = open(cur_file,'r')
			
			if output_dir is not None:
				out_filename = os.path.split(cur_file)[1]
				out_path = os.path.join(output_dir,out_filename)
				output = open(out_path,'w')
			else:
				output = None
				out_filename = None
				out_path = None
		except:
			raise
			log("Couldn't load file - skipping")
			continue

		try:
			process_instance.processor(data,mm,output)
		except:
			log("Problem using function to read or write data - skipping file")
			continue

		try:
			log("File complete")
			if output:
				log("Located at %s\n" % out_path)
				output.close()
			data.close()
		except:
			log("Couldn't close files - it's probably ok though - they'll get loaded again for the next file")
			continue

def shutdown():
	log_file.close()

