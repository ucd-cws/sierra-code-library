import os
import sys
import re


try:
	wdir = os.getcwd()
	input_dir = os.path.join(wdir,"input_files")
	output_dir = os.path.join(wdir,"output_files")
except:
	print "Couldn't set up working directory"
	sys.exit()

try:
	log_file = open(os.path.join(wdir,"log.txt"),'w')
except:
	print "Couldn't set up log"
	sys.exit()
	
def log(statement):
	print statement
	log_file.write("%s" % statement)

try:
	all_files = os.listdir(input_dir)
except:
	log("Couldn't get contents of input directory")

for cur_file in all_files:
        try:
        	log("Processing file %s" % cur_file)
                data = open(os.path.join(input_dir,cur_file),'r')
        	output = open(os.path.join(output_dir,cur_file),'w')
        except:
                log("Couldn't load file - skipping")
                continue

        try:
        	output.write("x y z i r g b\n")
                for line in data:
                        match = re.search('^(\d*)\s*$',line)
                        if match is not None and match.group(0) is not None:
                                continue # we don't care about this line
                        else:
                                output.write("%s" % line)
        except:
                log("Couldn't read or write data - skipping file")
                continue

        try:
                log("File complete - located at %s\n" % os.path.join(output_dir,cur_file))        
                output.close()
                data.close()
        except:
                log("Couldn't close files - it's probably ok though - they'll get loaded again for the next file")
                continue

log_file.close()

dummy = raw_input("Complete! Hit enter to exit")
